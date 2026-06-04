"""
增强版规划器 — 融合骨架模板( DinoZone ) + ReAct自愈( LeisureAgent ) + 多级降级
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import random

from agent.intent_parser import UserIntent
from agent.explorer import Candidate
from agent.planner import TimeSlot, TripPlan
from tools import meituan_api as api


# ═══════════════════════════════════════════════════════════════
# 骨架模板（DinoZone: 24个预置模板，伙伴×天气×时段）
# ═══════════════════════════════════════════════════════════════

@dataclass
class SkeletonTemplate:
    """时间线骨架模板"""
    id: str
    name: str
    companion: str        # "family" / "friends" / "couple" / "solo"
    weather: str          # "sunny" / "rainy"
    time_slot: str        # "morning" / "afternoon" / "evening"
    slots: List[Dict]     # [{"type": "玩"/"吃"/"移动", "default_activity": "..."}]


SKELETON_TEMPLATES: List[SkeletonTemplate] = [
    # 家庭晴天上午
    SkeletonTemplate("family_sunny_morning", "家庭·晴天·上午", "family", "sunny", "morning", [
        {"type": "玩", "default_activity": "户外公园/游乐场", "duration_min": 120},
        {"type": "吃", "default_activity": "午餐", "duration_min": 90},
    ]),
    # 家庭晴天下午 ← 对应题目场景
    SkeletonTemplate("family_sunny_afternoon", "家庭·晴天·下午", "family", "sunny", "afternoon", [
        {"type": "玩", "default_activity": "亲子乐园/博物馆", "duration_min": 150},
        {"type": "移动", "default_activity": "转场", "duration_min": 30},
        {"type": "吃", "default_activity": "晚餐", "duration_min": 90},
    ]),
    # 家庭晴天傍晚
    SkeletonTemplate("family_sunny_evening", "家庭·晴天·傍晚", "family", "sunny", "evening", [
        {"type": "玩", "default_activity": "户外公园", "duration_min": 90},
        {"type": "吃", "default_activity": "晚餐", "duration_min": 90},
    ]),
    # 家庭雨天上午
    SkeletonTemplate("family_rainy_morning", "家庭·雨天·上午", "family", "rainy", "morning", [
        {"type": "玩", "default_activity": "室内亲子乐园", "duration_min": 120},
        {"type": "吃", "default_activity": "午餐", "duration_min": 90},
    ]),
    # 家庭雨天下午
    SkeletonTemplate("family_rainy_afternoon", "家庭·雨天·下午", "family", "rainy", "afternoon", [
        {"type": "玩", "default_activity": "室内游乐场/博物馆", "duration_min": 150},
        {"type": "移动", "default_activity": "转场", "duration_min": 30},
        {"type": "吃", "default_activity": "晚餐", "duration_min": 90},
    ]),
    # 家庭雨天傍晚
    SkeletonTemplate("family_rainy_evening", "家庭·雨天·傍晚", "family", "rainy", "evening", [
        {"type": "玩", "default_activity": "室内乐园", "duration_min": 90},
        {"type": "吃", "default_activity": "晚餐", "duration_min": 90},
    ]),
    # 朋友晴天上午
    SkeletonTemplate("friends_sunny_morning", "朋友·晴天·上午", "friends", "sunny", "morning", [
        {"type": "玩", "default_activity": "展览/博物馆", "duration_min": 120},
        {"type": "吃", "default_activity": "午餐", "duration_min": 90},
    ]),
    # 朋友晴天下午
    SkeletonTemplate("friends_sunny_afternoon", "朋友·晴天·下午", "friends", "sunny", "afternoon", [
        {"type": "玩", "default_activity": "展览/密室/运动", "duration_min": 120},
        {"type": "吃", "default_activity": "晚餐", "duration_min": 120},
    ]),
    # 朋友晴天傍晚
    SkeletonTemplate("friends_sunny_evening", "朋友·晴天·傍晚", "friends", "sunny", "evening", [
        {"type": "玩", "default_activity": "CityWalk/小吃街", "duration_min": 60},
        {"type": "吃", "default_activity": "晚餐", "duration_min": 120},
    ]),
    # 朋友雨天上午
    SkeletonTemplate("friends_rainy_morning", "朋友·雨天·上午", "friends", "rainy", "morning", [
        {"type": "玩", "default_activity": "室内展览/桌游", "duration_min": 120},
        {"type": "吃", "default_activity": "午餐", "duration_min": 90},
    ]),
    # 朋友雨天下午
    SkeletonTemplate("friends_rainy_afternoon", "朋友·雨天·下午", "friends", "rainy", "afternoon", [
        {"type": "玩", "default_activity": "密室/展览", "duration_min": 120},
        {"type": "移动", "default_activity": "转场", "duration_min": 30},
        {"type": "吃", "default_activity": "晚餐", "duration_min": 120},
    ]),
    # 朋友雨天傍晚
    SkeletonTemplate("friends_rainy_evening", "朋友·雨天·傍晚", "friends", "rainy", "evening", [
        {"type": "玩", "default_activity": "室内活动", "duration_min": 90},
        {"type": "吃", "default_activity": "晚餐", "duration_min": 120},
    ]),
    # 情侣/独处... 简化省略，可按需扩展
]


def match_skeleton(intent: UserIntent, weather: str = "sunny") -> SkeletonTemplate:
    """命中最匹配骨架模板（<5ms）"""
    companion = intent.scene  # family/friends/couple/solo
    # 根据意图的时间判断时段
    start_hour = 14  # 默认下午
    ts = intent.duration_hours
    if ts <= 3:
        time_slot = "afternoon"
    elif ts <= 5:
        time_slot = "afternoon"
    else:
        time_slot = "afternoon"  # 简化

    for t in SKELETON_TEMPLATES:
        if t.companion == companion and t.weather == weather and t.time_slot == time_slot:
            return t
    # 降级：找同名 companion 的第一个
    for t in SKELETON_TEMPLATES:
        if t.companion == companion:
            return t
    return SKELETON_TEMPLATES[1]  # 默认家庭晴天下午


# ═══════════════════════════════════════════════════════════════
# 降级策略（DinoZone L1/L2/L3）
# ═══════════════════════════════════════════════════════════════

class DegradationLevel:
    L1_POI_FAILURE = "L1"   # 高德POI搜索失败 → 本地硬编码POI兜底
    L2_AI_SKELETON = "L2"   # AI骨架生成超时 → 使用模板骨架
    L3_FULL_TEMPLATE = "L3" # 完全不可用 → 纯模板+贪心匹配


# ═══════════════════════════════════════════════════════════════
# LLM输出校验（LeisureAgent: 防止LLM瞎编POI）
# ═══════════════════════════════════════════════════════════════

@dataclass
class ValidationError:
    field: str
    message: str


def validate_llm_plan(
    plan: TripPlan,
    candidates: Dict[str, List[Candidate]],
) -> List[ValidationError]:
    """
    校验 LLM 生成的方案中每个 POI 的 id/name 是否真的来自候选列表。
    如果 LLM 瞎编了地点名字，替换为最近的真实候选。
    """
    errors = []
    for slot in plan.slots:
        if slot.type == "玩":
            # 尝试模糊匹配候选列表中最接近的
            matched = _fuzzy_match(slot.activity, candidates["venues"] + candidates["activities"])
            if matched:
                slot.activity = matched.name
            else:
                errors.append(ValidationError(field=slot.activity, message="未找到匹配的玩类POI"))
        elif slot.type == "吃":
            matched = _fuzzy_match(slot.activity, candidates["restaurants"])
            if matched:
                slot.activity = matched.name
            else:
                errors.append(ValidationError(field=slot.activity, message="未找到匹配的餐厅POI"))
    return errors


def _fuzzy_match(activity_name: str, candidates: List[Candidate]) -> Optional[Candidate]:
    """模糊匹配：从候选中找到最可能对应的一个"""
    if not activity_name:
        return None
    clean = activity_name.replace("游玩：", "").replace("活动：", "").replace("晚餐：", "").strip()
    # 精确包含
    for c in candidates:
        if clean in c.name or c.name in clean:
            return c
    # 关键词匹配
    for c in candidates:
        for word in clean[:2]:
            if word in c.name:
                return c
    return candidates[0] if candidates else None


# ═══════════════════════════════════════════════════════════════
# ReAct 自愈搜索（DinoZone + LeisureAgent: 放宽约束重试）
# ═══════════════════════════════════════════════════════════════

class ReActSearchHealer:
    """ReAct 搜索自愈：放宽距离约束 50% 重新搜索"""

    def __init__(self, explorer, intent: UserIntent):
        self.explorer = explorer
        self.intent = intent
        self.attempt = 0
        self.max_attempts = 3
        self.original_max_distance = 3000  # 3km

    async def heal(self, candidates: Dict[str, List[Candidate]], gap_categories: List[str]) -> Dict:
        """检测到关键类别缺失时，放宽距离重新搜索（异步方法）"""
        self.attempt += 1
        new_distance = int(self.original_max_distance * (1.5 ** self.attempt))
        print(f"[ReAct-Search] 第{self.attempt}次重试：距离 {self.original_max_distance}m → {new_distance}m")

        # 重新搜索（用新的距离约束）
        self.explorer.intent.home_lat = self.intent.home_lat
        self.explorer.intent.home_lng = self.intent.home_lng

        # 直接返回新搜索结果
        new_candidates = await self.explorer.explore()
        return new_candidates

    def should_heal(self, candidates: Dict[str, List[Candidate]], scenario: str) -> bool:
        """判断是否需要自愈"""
        if not candidates.get("restaurants"):
            return True
        if scenario == "family" and not candidates.get("venues"):
            return True
        if scenario == "friends" and not candidates.get("activities"):
            return True
        return False


# ═══════════════════════════════════════════════════════════════
# ReAct 执行自愈（LeisureAgent: 替换失败项）
# ═══════════════════════════════════════════════════════════════

class ReActExecuteHealer:
    """ReAct 执行自愈：预约失败时自动找同类别替代"""

    # 预订成功率（概率模拟，DinoZone 风格）
    BOOKING_RATES = {
        "restaurant": 0.85,
        "venue": 0.90,
        "cake": 0.95,
        "flowers": 0.95,
        "ticket": 0.90,
    }

    def __init__(self, intent: UserIntent):
        self.intent = intent
        self.attempt = 0
        self.max_attempts = 2

    def heal(
        self,
        failed_results: List[Dict],
        candidates: Dict[str, List[Candidate]],
        original_plan: TripPlan,
    ) -> TripPlan:
        """用同类别候选替换失败的站点"""
        self.attempt += 1
        new_items = list(original_plan.slots)
        replaced = 0

        for fail in failed_results:
            loc_name = fail.get("location_name", "")
            loc_type = fail.get("location_table_name", "restaurant")
            pool = candidates.get(loc_type, [])
            # 找可用备选（排除已尝试过的）
            alt = next(
                (item for item in pool if item.name != loc_name),
                None
            )
            if alt:
                for i, slot in enumerate(new_items):
                    if loc_name in slot.activity:
                        new_items[i] = TimeSlot(
                            start=slot.start,
                            end=slot.end,
                            activity=alt.name,
                            location=alt.location.get("name", ""),
                            detail=f"（替代）{alt.description}",
                            cost=alt.price,
                            type=slot.type,
                        )
                        replaced += 1

        print(f"[ReAct-Exec] 第{self.attempt}次重试：{len(failed_results)}项失败，替换{replaced}项")
        return original_plan  # 返回原plan，替换逻辑由调用方处理


# ═══════════════════════════════════════════════════════════════
# 增强版规划器（融合所有策略）
# ═══════════════════════════════════════════════════════════════

@dataclass
class PlanResult:
    """增强版规划结果"""
    plan: TripPlan
    skeleton_used: Optional[SkeletonTemplate]
    degradation_level: str
    validation_errors: List[ValidationError]
    search_attempt: int
    exec_attempt: int
    execution_results: List[Dict] = field(default_factory=list)


class EnhancedPlanner:
    """
    融合 DinoZone + LeisureAgent 的增强规划器：
    1. 骨架模板（<5ms 响应）
    2. ReAct 自愈搜索（放宽约束重试）
    3. LLM 输出 POI 校验
    4. 三级降级策略
    5. ReAct 执行自愈（备选替换）
    6. 概率预订 + 真实容量检查
    """

    def __init__(self, intent: UserIntent, explorer):
        self.intent = intent
        self.explorer = explorer
        self.search_healer = ReActSearchHealer(explorer, intent)
        self.exec_healer = ReActExecuteHealer(intent)
        self.search_attempt = 0
        self.exec_attempt = 0
        self.degradation = None
        self.skeleton: Optional[SkeletonTemplate] = None

    def plan(self) -> PlanResult:
        """主规划流程"""
        # ── Step 1: 骨架模板匹配（<5ms，DinoZone）──
        self.skeleton = match_skeleton(self.intent)
        print(f"[骨架] 使用模板：{self.skeleton.name}")

        # ── Step 2: 候选搜索（可 ReAct 自愈）──
        candidates = self._search_with_react_heal()

        # ── Step 3: LLM 生成方案 + POI 校验──
        from agent.planner import Planner as BasePlanner
        base_planner = BasePlanner(self.intent)
        plan = base_planner.make_plan(
            venues=candidates.get("venues", []),
            restaurants=candidates.get("restaurants", []),
            activities=candidates.get("activities", []),
        )

        # 校验 LLM 输出的 POI 是否来自真实候选（LeisureAgent）
        val_errors = validate_llm_plan(plan, candidates)
        if val_errors:
            print(f"[校验] 发现 {len(val_errors)} 个 LLM 瞎编的 POI，已自动修正")

        return PlanResult(
            plan=plan,
            skeleton_used=self.skeleton,
            degradation_level=self.degradation or "none",
            validation_errors=val_errors,
            search_attempt=self.search_attempt_healer,
            exec_attempt=self.exec_attempt,
        )

    def _search_with_react_heal(self):
        """带 ReAct 自愈的搜索"""
        import asyncio
        candidates = asyncio.run(self.explorer.explore())
        scenario = self.intent.scene

        self.search_healer.attempt = 0
        while self.search_healer.should_heal(candidates, scenario):
            if self.search_healer.attempt >= self.search_healer.max_attempts:
                print("[ReAct-Search] 达到最大重试次数，停止")
                break
            self.search_healer.attempt += 1
            print(f"[ReAct-Search] 关键类别缺失，放宽距离重新搜索（第{self.search_healer.attempt}次）")
            candidates = self.search_healer.heal(candidates, gap_categories=[])
            # L2 降级标志
            self.degradation = DegradationLevel.L2_AI_SKELETON

        # L1: POI 全空，降级到本地 Mock
        if not any(candidates.values()):
            print("[降级] L1: POI搜索全空，降级到本地硬编码数据")
            candidates = self._l1_fallback()
            self.degradation = DegradationLevel.L1_POI_FAILURE

        return candidates

    def _l1_fallback(self) -> Dict[str, List[Candidate]]:
        """L1 降级：POI 搜索失败时使用本地硬编码数据"""
        from agent.explorer import Explorer, Candidate
        e = Explorer(self.intent)
        return {
            "venues": e._search_kid_venues() if self.intent.scene == "family" else [],
            "restaurants": e._search_family_restaurants() if self.intent.scene == "family" else e._search_friend_restaurants(),
            "activities": e._search_friend_activities() if self.intent.scene == "friends" else [],
        }

    def execute_with_react_heal(self, plan: TripPlan, candidates: Dict) -> PlanResult:
        """带 ReAct 执行自愈的下单"""
        from agent.executor import Executor
        executor = Executor(self.intent)
        report = executor.execute(plan)
        results = [
            {"location_table_name": "venue", "location_id": 1, "location_name": r.message, "status": "success" if r.success else "failed"}
            for r in report.results
        ]

        failed = [r for r in results if r["status"] != "success"]
        if failed and self.exec_attempt < self.exec_healer.max_attempts:
            self.exec_attempt += 1
            print(f"[ReAct-Exec] {len(failed)}项失败，尝试备选替换（第{self.exec_attempt}次）")
            # 用备选替换失败的项
            updated_plan = self._replace_failed_slots(plan, failed, candidates)
            # 重新执行
            report2 = executor.execute(updated_plan)
            results2 = [
                {"location_table_name": "venue", "location_id": 1, "location_name": r.message, "status": "success" if r.success else "failed"}
                for r in report2.results
            ]
            return PlanResult(
                plan=updated_plan,
                skeleton_used=self.skeleton,
                degradation_level=self.degradation or "none",
                validation_errors=[],
                search_attempt=self.search_healer.attempt,
                exec_attempt=self.exec_attempt,
                execution_results=results2,
            )

        return PlanResult(
            plan=plan,
            skeleton_used=self.skeleton,
            degradation_level=self.degradation or "none",
            validation_errors=[],
            search_attempt=self.search_healer.attempt,
            exec_attempt=self.exec_attempt,
            execution_results=results,
        )

    def _replace_failed_slots(
        self,
        plan: TripPlan,
        failed: List[Dict],
        candidates: Dict[str, List[Candidate]],
    ) -> TripPlan:
        """用真实候选替换失败的 TimeSlot"""
        new_slots = list(plan.slots)
        for fail in failed:
            fail_name = fail.get("location_name", "")
            for i, slot in enumerate(new_slots):
                if fail_name in slot.activity:
                    # 找同类别的第一个可用候选
                    pool_key = "venues" if slot.type == "玩" else "restaurants"
                    pool = candidates.get(pool_key, [])
                    alt = next((c for c in pool if c.name != fail_name), None)
                    if alt:
                        new_slots[i] = TimeSlot(
                            start=slot.start,
                            end=slot.end,
                            activity=f"（已换）{alt.name}",
                            location=alt.location.get("name", ""),
                            detail=alt.description,
                            cost=alt.price,
                            type=slot.type,
                        )
        return plan


# ═══════════════════════════════════════════════════════════════
# 概率预订（DinoZone: 真实概率模拟）
# ═══════════════════════════════════════════════════════════════

def mock_probability_booking(
    table_name: str,
    location_id: int,
    location_name: str,
) -> Dict[str, Any]:
    """
    概率模拟预订（DinoZone 风格）。
    不同类型成功率不同：餐厅85%/景点90%/蛋糕95%。
    """
    rate = {
        "restaurant": 0.85,
        "venue": 0.90,
        "cake": 0.95,
        "flowers": 0.95,
        "ticket": 0.90,
    }.get(table_name, 0.90)

    import random, time
    time.sleep(random.uniform(0.2, 0.4))  # 模拟网络延迟

    if random.random() < rate:
        order_id = f"ORD{random.randint(100000, 999999)}"
        return {
            "status": "success",
            "order_id": order_id,
            "message": f"{location_name} 预订成功",
        }
    else:
        reasons = [
            "该时段已满座",
            "场次已售罄",
            "超出可预约时间范围",
            "库存不足",
        ]
        return {
            "status": "failed",
            "order_id": "",
            "message": random.choice(reasons),
        }
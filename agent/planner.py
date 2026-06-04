"""
规划器 — 从候选方案构建可执行的带时间轴的计划
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from agent.intent_parser import UserIntent
from agent.explorer import Candidate


@dataclass
class TimeSlot:
    """时间槽"""
    start: str      # "HH:MM"
    end: str        # "HH:MM"
    activity: str   # 活动名称
    location: str   # 地点
    detail: Optional[str] = None
    cost: float = 0.0
    type: str = ""  # "玩" / "吃" / "配送"


@dataclass
class TripPlan:
    """完整行程计划"""
    scene: str
    date: str
    duration_hours: float
    slots: List[TimeSlot] = field(default_factory=list)
    total_budget: float = 0.0
    warnings: List[str] = field(default_factory=list)
    notes: str = ""


class Planner:
    """规划器：生成可执行的时间轴计划"""

    def __init__(self, intent: UserIntent):
        self.intent = intent

    def make_plan(
        self,
        venues: List[Candidate],
        restaurants: List[Candidate],
        activities: List[Candidate],
    ) -> TripPlan:
        """
        综合所有候选，构建带时间轴的行程
        """
        plan = TripPlan(
            scene=self.intent.scene,
            date=self.intent.date or "2026-06-04",
            duration_hours=self.intent.duration_hours,
        )

        if self.intent.scene == "family":
            self._plan_family(plan, venues, restaurants)
        elif self.intent.scene == "friends":
            self._plan_friends(plan, venues, restaurants, activities)
        else:
            # couple / solo / 未知场景：复用通用的活动+餐厅排程逻辑
            self._plan_friends(plan, venues, restaurants, activities)

        self._calc_budget(plan)
        return plan

    def _plan_family(self, plan: TripPlan, venues: List[Candidate], restaurants: List[Candidate]):
        """家庭场景规划"""
        # 排序：优先亲子乐园 > 公园 > 博物馆
        venues = sorted(venues, key=lambda v: (
            "亲子乐园" in v.category,
            "博物馆" in v.category,
            "户外公园" in v.category,
            v.rating,
        ), reverse=True)

        best_venue = venues[0] if venues else None

        # 时间窗口：14:00出发 → 14:30-17:00玩 → 17:30晚餐
        slots = []

        if best_venue:
            slots.append(TimeSlot(
                start="14:00",
                end="14:30",
                activity="前往亲子乐园",
                location=best_venue.location.get("name", ""),
                detail=f"【{best_venue.name}】{best_venue.description}",
                cost=best_venue.price,
                type="玩",
            ))
            slots.append(TimeSlot(
                start="14:30",
                end="17:00",
                activity=f"游玩：{best_venue.name}",
                location=best_venue.location.get("name", ""),
                detail=f"开放时间：{best_venue.open_hours}，"
                       f"评分：{best_venue.rating}，"
                       f"门票：{best_venue.price}元/人" if best_venue.price > 0 else "免费",
                cost=best_venue.price,
                type="玩",
            ))

        # 餐厅（老婆减肥优先轻食）
        dinner = self._pick_restaurant(restaurants, prefer_diet=True)
        if dinner:
            slots.append(TimeSlot(
                start="17:00",
                end="17:30",
                activity="转场前往餐厅",
                location=dinner.location.get("name", ""),
                type="移动",
            ))
            slots.append(TimeSlot(
                start="17:30",
                end="19:00",
                activity=f"晚餐：{dinner.name}",
                location=dinner.location.get("name", ""),
                detail=f"人均：{dinner.price}元，"
                       f"评分：{dinner.rating}，"
                       f"标签：{', '.join(dinner.tags)}",
                cost=dinner.price * (2 + 1),  # 2大人+1小孩估算
                type="吃",
            ))

        # 配送：蛋糕/鲜花（可选）
        if self.intent.needs_delivery:
            plan.slots.append(TimeSlot(
                start="18:00",
                end="18:30",
                activity=self._delivery_desc(),
                location="送至餐厅",
                type="配送",
            ))

        plan.slots = slots

    def _plan_friends(
        self,
        plan: TripPlan,
        venues: List[Candidate],
        restaurants: List[Candidate],
        activities: List[Candidate],
    ):
        """朋友聚会场景规划"""
        # 优先密室/展览/运动
        activities = sorted(activities, key=lambda a: a.rating, reverse=True)
        best_activity = activities[0] if activities else None

        slots = []

        if best_activity:
            slots.append(TimeSlot(
                start="14:00",
                end="14:30",
                activity="出发前往活动地点",
                location=best_activity.location.get("name", ""),
                type="移动",
            ))
            slots.append(TimeSlot(
                start="14:30",
                end="16:30",
                activity=f"活动：{best_activity.name}",
                location=best_activity.location.get("name", ""),
                detail=f"{best_activity.description}，"
                       f"门票：{best_activity.price}元/人",
                cost=best_activity.price * self.intent.group_size,
                type="玩",
            ))

        # 小吃街/CityWalk（可选过渡）
        if venues:
            walk = venues[0]
            slots.append(TimeSlot(
                start="16:30",
                end="17:30",
                activity=f"CityWalk：{walk.name}",
                location=walk.location.get("name", ""),
                detail=walk.description,
                cost=0.0,
                type="玩",
            ))

        # 餐厅
        dinner = self._pick_restaurant(restaurants, prefer_diet=False)
        if dinner:
            slots.append(TimeSlot(
                start="17:30",
                end="17:45",
                activity="前往餐厅",
                location=dinner.location.get("name", ""),
                type="移动",
            ))
            slots.append(TimeSlot(
                start="17:45",
                end="19:30",
                activity=f"晚餐：{dinner.name}",
                location=dinner.location.get("name", ""),
                detail=f"人均：{dinner.price}元，{dinner.description}",
                cost=dinner.price * self.intent.group_size,
                type="吃",
            ))

        # 蛋糕/鲜花
        if self.intent.needs_delivery:
            slots.append(TimeSlot(
                start="18:00",
                end="18:30",
                activity=self._delivery_desc(),
                location="送至餐厅",
                type="配送",
            ))

        plan.slots = slots

    def _pick_restaurant(
        self,
        restaurants: List[Candidate],
        prefer_diet: bool = False,
    ) -> Optional[Candidate]:
        """选择一个最优餐厅"""
        if not restaurants:
            return None
        # 有位的优先
        available = [r for r in restaurants if r.score > 0]
        if not available:
            return restaurants[0]
        # 减肥模式优先轻食标签
        if prefer_diet:
            diet = [r for r in available if any(t in ["轻食", "沙拉", "健康"] for t in r.tags)]
            if diet:
                return diet[0]
        return available[0]

    def _delivery_desc(self) -> str:
        """配送描述"""
        item_map = {
            "cake": "🎂 生日蛋糕配送（好利来·6寸草莓鲜奶蛋糕 168元）",
            "flowers": "🌹 鲜花配送（野兽派·11朵红玫瑰 158元）",
        }
        return item_map.get(self.intent.delivery_item, "🎁 配送至餐厅")

    def _calc_budget(self, plan: TripPlan):
        """计算总预算"""
        total = sum(s.cost for s in plan.slots)
        plan.total_budget = total


def _slot_minutes(start: str, end: str) -> int:
    """计算时间槽时长（分钟）。解析失败返回 0。"""
    try:
        sh, sm = map(int, start.split(":"))
        eh, em = map(int, end.split(":"))
        return max(0, (eh * 60 + em) - (sh * 60 + sm))
    except (ValueError, AttributeError):
        return 0


_SCENE_TITLE = {
    "family": "亲子下午时光",
    "friends": "朋友聚会下午",
    "couple": "二人约会下午",
    "solo": "个人休闲下午",
}


def format_plan_json(plan: TripPlan) -> dict:
    """
    将 TripPlan 转为前端时间轴卡片所需的 JSON 结构。
    规则降级路径用它替代 Markdown，使前端始终走结构化渲染。

    输出字段与前端 PlanContent 对齐：
      title / description / total_cost / items[{type, activity,
      location_name, arrive_time, leave_time, stay_minute, cost}]
    """
    title = _SCENE_TITLE.get(plan.scene, "休闲行程")
    n = len(plan.slots)
    cost = plan.total_budget
    description = f"为你规划了 {n} 个行程站点，预计总花费约 {cost:.0f} 元。" if n else "暂未找到合适的候选地点。"

    items = [
        {
            "type": slot.type or "玩",
            "activity": slot.activity,
            "location_name": slot.location,
            "arrive_time": slot.start,
            "leave_time": slot.end,
            "stay_minute": _slot_minutes(slot.start, slot.end),
            "cost": round(slot.cost),
            "detail": slot.detail or "",
        }
        for slot in plan.slots
    ]

    return {
        "title": title,
        "description": description,
        "total_cost": round(cost),
        "items": items,
    }


def format_plan_md(plan: TripPlan) -> str:
    """格式化输出为 Markdown"""
    date_display = plan.date
    lines = [
        f"# 📋 行程安排 — {date_display}（{plan.scene}场景）\n",
        f"**总预算：约 {plan.total_budget:.0f} 元**\n",
        "---\n",
    ]
    for i, slot in enumerate(plan.slots, 1):
        emoji = {"玩": "🎯", "吃": "🍽️", "移动": "🚗", "配送": "📦"}.get(slot.type, "•")
        lines.append(f"### {i}. {emoji} {slot.activity}")
        lines.append(f"**时间：** {slot.start} → {slot.end}")
        lines.append(f"**地点：** {slot.location}")
        if slot.detail:
            lines.append(f"**详情：** {slot.detail}")
        if slot.cost > 0:
            lines.append(f"**费用：** {slot.cost:.0f} 元")
        lines.append("")

    if plan.warnings:
        lines.append("\n---\n⚠️ **注意：**\n")
        for w in plan.warnings:
            lines.append(f"- {w}")

    lines.append("\n---\n✅ **确认方案后，系统将自动完成景点门票下单、餐厅订座及配送预约。**")
    return "\n".join(lines)
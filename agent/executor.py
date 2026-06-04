"""
执行器 — 将计划转换为可执行的下单/预约操作
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set

from agent.intent_parser import UserIntent
from agent.planner import TripPlan
from tools import meituan_api as api


@dataclass
class OrderResult:
    """单个订单的执行结果"""
    success: bool
    order_type: str    # "ticket" / "booking" / "delivery"
    order_id: str = ""
    message: str = ""
    data: Dict = field(default_factory=dict)


@dataclass
class ExecutionReport:
    """执行报告"""
    plan: TripPlan
    results: List[OrderResult] = field(default_factory=list)
    all_success: bool = False

    def summary(self) -> str:
        lines = ["## 📦 订单执行报告\n"]
        for r in self.results:
            status = "✅" if r.success else "❌"
            lines.append(f"{status} **{r.order_type}**：{r.message}")
            if r.order_id:
                lines.append(f"   订单号：`{r.order_id}`")
        lines.append("")
        if self.all_success:
            lines.append("✅ **全部订单已完成，可凭二维码到店使用。**")
        else:
            lines.append("⚠️ 部分订单需手动确认，请点击上述订单号处理。")
        return "\n".join(lines)


class Executor:
    """执行器：将行程计划转化为可执行的下单操作"""

    def __init__(self, intent: UserIntent):
        self.intent = intent

    def execute(self, plan: TripPlan) -> ExecutionReport:
        """
        遍历行程中的每个 TimeSlot，按类型调用对应 API
        """
        report = ExecutionReport(plan=plan)
        orders = []
        ordered_venue_ids: Set[str] = set()
        ordered_restaurant_ids: Set[str] = set()

        for slot in plan.slots:
            if slot.type == "玩":
                venue_name = slot.activity.replace("游玩：", "").replace("活动：", "")
                result = self._create_ticket_order(venue_name, slot, ordered_venue_ids)
                orders.append(result)

            elif slot.type == "吃":
                restaurant_name = slot.activity.replace("晚餐：", "")
                result = self._create_booking(restaurant_name, slot, ordered_restaurant_ids)
                orders.append(result)

            elif slot.type == "配送":
                result = self._create_delivery(slot)
                orders.append(result)

        report.results = orders
        report.all_success = all(r.success for r in orders)
        return report

    def _create_ticket_order(
        self, name: str, slot, already_ordered: Set[str]
    ) -> OrderResult:
        """创建门票订单（Mock），避免重复下单同一场馆"""
        venue_id = self._guess_venue_id(name)
        if venue_id in already_ordered:
            return OrderResult(
                success=True,
                order_type="ticket",
                order_id="",
                message=f"跳过（已下单）：{name}",
                data={},
            )
        resp = api.ticket_create(
            venue_id=venue_id,
            ticket_type="儿童/成人票",
            quantity=self._adult_count(),
        )
        if resp.code == 0:
            d = resp.data
            already_ordered.add(venue_id)
            return OrderResult(
                success=True,
                order_type="ticket",
                order_id=d["ticket_id"],
                message=f"景点门票下单成功：{d['venue_name']} ×{d['quantity']}张，"
                        f"共 {d['total_price']} 元",
                data=d,
            )
        return OrderResult(
            success=False,
            order_type="ticket",
            message=f"景点门票下单失败：{resp.message}",
        )

    def _create_booking(
        self, restaurant_name: str, slot, already_booked: Set[str]
    ) -> OrderResult:
        """创建餐厅订座（Mock），避免重复订座同一餐厅"""
        restaurant_id = self._guess_restaurant_id(restaurant_name)
        if restaurant_id in already_booked:
            return OrderResult(
                success=True,
                order_type="booking",
                order_id="",
                message=f"跳过（已订座）：{restaurant_name}",
                data={},
            )
        resp = api.table_booking(
            restaurant_id=restaurant_id,
            date=self.intent.date or "2026-06-04",
            time=slot.start.replace(":", ""),
            people=self._adult_count(),
        )
        if resp.code == 0:
            d = resp.data
            already_booked.add(restaurant_id)
            return OrderResult(
                success=True,
                order_type="booking",
                order_id=d["booking_id"],
                message=f"餐厅订座成功：{d['restaurant_name']} {d['date']} {d['time']}，"
                        f"{d['people']}人",
                data=d,
            )
        # 订座失败，尝试备选餐厅
        fallback_id = self._get_fallback_restaurant_id(restaurant_id)
        if fallback_id and fallback_id not in already_booked:
            resp2 = api.table_booking(
                restaurant_id=fallback_id,
                date=self.intent.date or "2026-06-04",
                time=slot.start.replace(":", ""),
                people=self._adult_count(),
            )
            if resp2.code == 0:
                d2 = resp2.data
                already_booked.add(fallback_id)
                return OrderResult(
                    success=True,
                    order_type="booking",
                    order_id=d2["booking_id"],
                    message=f"原餐厅满座，已自动切换至{d2['restaurant_name']}订座成功",
                    data=d2,
                )
        return OrderResult(
            success=False,
            order_type="booking",
            message=f"餐厅订座失败：{resp.message}",
        )

    def _create_delivery(self, slot) -> OrderResult:
        """创建配送订单（Mock）"""
        item_map = {"cake": "d001", "flowers": "d002"}
        item_id = item_map.get(self.intent.delivery_item, "d001")
        resp = api.delivery_order(
            item_id=item_id,
            address=slot.location,
            deliver_time=f"{self.intent.date} {slot.start}",
            remark="庆祝用",
        )
        if resp.code == 0:
            d = resp.data
            return OrderResult(
                success=True,
                order_type="delivery",
                order_id=d["order_id"],
                message=f"配送订单已确认：{d['item_name']}（{d['shop_name']}），"
                        f"预计 {d['eta']} 到达",
                data=d,
            )
        return OrderResult(
            success=False,
            order_type="delivery",
            message=f"配送下单失败：{resp.message}",
        )

    def _adult_count(self) -> int:
        """估算大人数量"""
        if self.intent.scene == "family":
            return 2
        elif self.intent.scene == "friends":
            return self.intent.group_size
        return 2

    def _guess_venue_id(self, name: str) -> str:
        """从名称推测 venue_id（Mock）"""
        if "公园" in name:
            return "v001"
        if "大悦城" in name or "奇宝" in name:
            return "v002"
        if "自然博物馆" in name:
            return "v003"
        if "乐高" in name:
            return "v004"
        if "teamLab" in name or "艺术展" in name:
            return "a001"
        if "小吃街" in name or "CityWalk" in name:
            return "a002"
        if "密室" in name:
            return "a003"
        return "v002"

    def _guess_restaurant_id(self, name: str) -> str:
        """从名称推测 restaurant_id（Mock）"""
        if "Salad" in name or "沙拉" in name or "轻食" in name:
            return "r001"
        if "粤江" in name or "粤菜" in name:
            return "r002"
        if "海底捞" in name:
            return "r003"
        if "西堤" in name or "牛排" in name:
            return "r004"
        if "鹿港" in name or "台菜" in name:
            return "r005"
        return "r002"

    def _get_fallback_restaurant_id(self, original_id: str) -> str | None:
        """获取备选餐厅"""
        fallback_map = {
            "r001": "r002",  # 轻食 → 粤菜
            "r002": "r005",  # 粤菜 → 台菜
            "r003": "r002",  # 海底捞 → 粤菜
            "r004": "r002",  # 西堤 → 粤菜
            "r005": "r002",  # 台菜 → 粤菜
        }
        return fallback_map.get(original_id)
"""
美团 API Mock 实现
所有接口均为模拟实现，用于 Demo 演示
"""

import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .mock_data import (
    MOCK_VENUES, MOCK_FRIEND_ACTIVITIES, MOCK_RESTAURANTS,
    MOCK_DELIVERY_ITEMS, MOCK_LOCATIONS,
    POI, Restaurant, DeliveryItem, Location
)
from . import amap_api


# ========== 通用响应封装 ==========

@dataclass
class ApiResponse:
    code: int = 0
    message: str = "ok"
    data: Any = None


def ok(data: Any) -> ApiResponse:
    return ApiResponse(code=0, message="ok", data=data)


def err(msg: str, code: int = 1) -> ApiResponse:
    return ApiResponse(code=code, message=msg, data=None)


# ========== 工具接口 ==========

def location_nearby_search(
    keywords: List[str],
    lat: float,
    lng: float,
    radius_km: float = 3.0,
    category: Optional[str] = None,
) -> ApiResponse:
    """
    搜索附近地点。
    优先调用高德真实 POI（配置了 AMAP_API_KEY 时）；失败或未配置则回退 mock 数据。
    """
    # ── 真实数据路径：高德周边搜索 ──
    real = amap_api.around_search(keywords=keywords, lat=lat, lng=lng, radius_km=radius_km)
    if real is not None:
        if category:
            real = [p for p in real if p.get("category") == category]
        return ok({"pois": real, "total": len(real), "source": "amap"})

    # ── 回退路径：mock 数据 ──
    candidates = MOCK_VENUES + MOCK_FRIEND_ACTIVITIES
    results = []
    for v in candidates:
        if category and v.category != category:
            continue
        # 简单距离模拟：随机接受（实际按经纬度计算）
        score = random.random()
        if score > 0.3:  # ~70% 通过
            results.append({
                "id": v.id,
                "name": v.name,
                "category": v.category,
                "location": {"lat": v.location.lat, "lng": v.location.lng, "name": v.location.name},
                "rating": v.rating,
                "price": v.price,
                "tags": v.tags,
                "description": v.description,
                "open_hours": v.open_hours or "10:00-21:00",
            })
    return ok({"pois": results, "total": len(results), "source": "mock"})


def restaurant_search(
    cuisine: Optional[str] = None,
    lat: float = 0.0,
    lng: float = 0.0,
    radius_km: float = 3.0,
    max_avg_price: Optional[float] = None,
    tags: Optional[List[str]] = None,
    require_availability: bool = False,
) -> ApiResponse:
    """
    搜索餐厅。
    优先调用高德真实 POI（配置了 AMAP_API_KEY 时）；失败或未配置则回退 mock 数据。
    高德无「是否有位」信息，真实路径下 require_availability 不做硬过滤（默认视为可订）。
    """
    # ── 真实数据路径：高德周边搜索（餐饮类关键词）──
    kw = [cuisine] if cuisine else ["餐厅", "美食", "饭店"]
    real = amap_api.around_search(keywords=kw, lat=lat, lng=lng, radius_km=radius_km)
    if real is not None:
        results = []
        for p in real:
            avg = p.get("price", 0.0)
            if max_avg_price and avg and avg > max_avg_price:
                continue
            results.append({
                "id": p["id"],
                "name": p["name"],
                "cuisine": p.get("category", "餐厅"),
                "location": p["location"],
                "avg_price": avg,
                "rating": p.get("rating", 0.0),
                "tags": p.get("tags", []),
                "has_availability": True,        # 高德无此信息，默认可订
                "queue_time_min": 0,
                "description": p.get("description", ""),
            })
        return ok({"restaurants": results, "total": len(results), "source": "amap"})

    # ── 回退路径：mock 数据 ──
    results = []
    for r in MOCK_RESTAURANTS:
        if cuisine and cuisine not in r.cuisine and r.cuisine not in cuisine:
            pass  # 跳过不匹配
        if max_avg_price and r.avg_price > max_avg_price:
            continue
        if require_availability and not r.has_availability:
            continue
        results.append({
            "id": r.id,
            "name": r.name,
            "cuisine": r.cuisine,
            "location": {"lat": r.location.lat, "lng": r.location.lng, "name": r.location.name},
            "avg_price": r.avg_price,
            "rating": r.rating,
            "tags": r.tags,
            "has_availability": r.has_availability,
            "queue_time_min": r.queue_time_min,
            "description": r.description,
        })
    return ok({"restaurants": results, "total": len(results), "source": "mock"})


def venue_detail(venue_id: str) -> ApiResponse:
    """
    获取景点/活动详情
    """
    all_venues = {v.id: v for v in MOCK_VENUES + MOCK_FRIEND_ACTIVITIES}
    v = all_venues.get(venue_id)
    if not v:
        return err("venue not found", code=404)
    return ok({
        "id": v.id,
        "name": v.name,
        "category": v.category,
        "location": {"lat": v.location.lat, "lng": v.location.lng, "name": v.location.name},
        "rating": v.rating,
        "price": v.price,
        "tags": v.tags,
        "description": v.description,
        "open_hours": v.open_hours or "10:00-21:00",
        "ticket_types": [
            {"name": "成人票", "price": v.price if v.price > 0 else 0},
            {"name": "儿童票", "price": max(v.price * 0.5, 0) if v.price > 0 else 0},
        ] if v.price > 0 else [{"name": "免费", "price": 0}],
    })


def table_booking(
    restaurant_id: str,
    date: str,          # "YYYY-MM-DD"
    time: str,          # "HH:MM"
    people: int,
) -> ApiResponse:
    """
    餐厅订座
    """
    r = next((r for r in MOCK_RESTAURANTS if r.id == restaurant_id), None)
    if not r:
        return err("restaurant not found", code=404)

    if not r.has_availability:
        return err(
            f"餐厅当前满座，预计排队 {r.queue_time_min} 分钟",
            code=101,
        )

    if people > r.seats:
        return err(f"座位不足，当前剩余 {r.seats} 个", code=102)

    booking_id = f"BK{random.randint(100000, 999999)}"
    return ok({
        "booking_id": booking_id,
        "restaurant_name": r.name,
        "date": date,
        "time": time,
        "people": people,
        "status": "confirmed",
        "note": f"请按时到店，餐厅地址：{r.location.name}",
    })


def ticket_create(
    venue_id: str,
    ticket_type: str,
    quantity: int = 1,
    user_name: str = "",
    phone: str = "",
) -> ApiResponse:
    """
    创建门票订单
    """
    v = next((v for v in MOCK_VENUES + MOCK_FRIEND_ACTIVITIES if v.id == venue_id), None)
    if not v:
        return err("venue not found", code=404)

    unit_price = v.price if v.price > 0 else 0
    ticket_id = f"TK{random.randint(100000, 999999)}"
    return ok({
        "ticket_id": ticket_id,
        "venue_name": v.name,
        "ticket_type": ticket_type,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": unit_price * quantity,
        "status": "confirmed",
        "qr_code": f"https://meituan.com/ticket/{ticket_id}",
    })


def delivery_order(
    item_id: str,
    address: str,
    deliver_time: str,   # "YYYY-MM-DD HH:MM"
    remark: str = "",
) -> ApiResponse:
    """
    创建配送订单（蛋糕/鲜花）
    """
    item = next((i for i in MOCK_DELIVERY_ITEMS if i.id == item_id), None)
    if not item:
        return err("item not found", code=404)

    order_id = f"DL{random.randint(100000, 999999)}"
    # 模拟配送到达时间
    eta = datetime.now() + timedelta(minutes=random.randint(30, 60))
    return ok({
        "order_id": order_id,
        "item_name": item.name,
        "shop_name": item.shop_name,
        "price": item.price,
        "address": address,
        "deliver_time": deliver_time,
        "eta": eta.strftime("%Y-%m-%d %H:%M"),
        "status": "confirmed",
        "remark": remark,
    })


def generate_order_summary(orders: List[Dict]) -> Dict:
    """
    生成订单汇总
    """
    total = sum(o.get("total_price", 0) for o in orders)
    return {
        "orders": orders,
        "total_amount": total,
        "order_count": len(orders),
    }
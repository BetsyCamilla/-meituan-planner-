"""
探索器 — 并行搜索多个来源的候选活动/餐厅
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from agent.intent_parser import UserIntent
from tools import meituan_api as api


@dataclass
class Candidate:
    """候选项目（景点/餐厅/活动）"""
    id: str
    name: str
    category: str
    location: Dict[str, Any]
    rating: float = 0.0
    price: float = 0.0
    tags: List[str] = field(default_factory=list)
    description: str = ""
    open_hours: str = ""
    source: str = ""  # "venue" / "restaurant" / "activity"
    score: float = 0.0  # 综合评分


class Explorer:
    """探索器：并行搜索玩/吃/活动候选"""

    def __init__(self, intent: UserIntent):
        self.intent = intent
        self.home_lat = intent.home_lat
        self.home_lng = intent.home_lng
        self._search_cache = {}  # 缓存搜索结果

    async def explore(self) -> Dict[str, List[Candidate]]:
        """
        并行探索所有候选
        返回 {"venues": [...], "restaurants": [...], "activities": [...]}
        """
        # 生成缓存key
        cache_key = f"{self.intent.scene}_{self.home_lat}_{self.home_lng}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        if self.intent.scene == "family":
            venues, restaurants, activities = await self._explore_family()
        elif self.intent.scene == "friends":
            venues, restaurants, activities = await self._explore_friends()
        elif self.intent.scene == "couple":
            venues, restaurants, activities = await self._explore_couple()
        else:  # solo 及任何未知场景，给出通用兜底候选
            venues, restaurants, activities = await self._explore_generic()

        result = {
            "venues": venues,
            "restaurants": restaurants,
            "activities": activities,
        }
        
        # 缓存结果
        self._search_cache[cache_key] = result
        return result

    async def _explore_family(self) -> tuple:
        """家庭场景探索"""
        # 并行执行三个搜索
        f1 = asyncio.get_event_loop().run_in_executor(
            None, self._search_kid_venues
        )
        f2 = asyncio.get_event_loop().run_in_executor(
            None, self._search_family_restaurants
        )
        f3 = asyncio.get_event_loop().run_in_executor(
            None, self._search_outdoor_parks
        )

        venues, restaurants, activities = await asyncio.gather(f1, f2, f3)
        return venues, restaurants, activities

    async def _explore_friends(self) -> tuple:
        """朋友聚会场景探索"""
        f1 = asyncio.get_event_loop().run_in_executor(
            None, self._search_friend_activities
        )
        f2 = asyncio.get_event_loop().run_in_executor(
            None, self._search_friend_restaurants
        )
        f3 = asyncio.get_event_loop().run_in_executor(
            None, self._search_kid_venues  # 复用，不适合朋友但留空
        )

        activities, restaurants, venues = await asyncio.gather(f1, f2, f3)
        return venues, restaurants, activities

    async def _explore_couple(self) -> tuple:
        """情侣约会场景：偏好有氛围的活动 + 餐厅 + 景点。复用现有搜索方法。"""
        loop = asyncio.get_event_loop()
        f1 = loop.run_in_executor(None, self._search_friend_activities)
        f2 = loop.run_in_executor(None, self._search_friend_restaurants)
        f3 = loop.run_in_executor(None, self._search_outdoor_parks)
        activities, restaurants, venues = await asyncio.gather(f1, f2, f3)
        return venues, restaurants, activities

    async def _explore_generic(self) -> tuple:
        """单人 / 未知场景兜底：通用活动 + 餐厅，保证不返回空候选。"""
        loop = asyncio.get_event_loop()
        f1 = loop.run_in_executor(None, self._search_friend_activities)
        f2 = loop.run_in_executor(None, self._search_friend_restaurants)
        f3 = loop.run_in_executor(None, self._search_outdoor_parks)
        activities, restaurants, venues = await asyncio.gather(f1, f2, f3)
        return venues, restaurants, activities

    def _search_kid_venues(self) -> List[Candidate]:
        """搜索亲子乐园/博物馆"""
        resp = api.location_nearby_search(
            keywords=["亲子乐园", "儿童游乐", "博物馆", "亲子"],
            lat=self.home_lat,
            lng=self.home_lng,
            radius_km=3.0,
        )
        if resp.code != 0:
            return []
        return [
            Candidate(
                id=p["id"],
                name=p["name"],
                category=p["category"],
                location=p["location"],
                rating=p["rating"],
                price=p["price"],
                tags=p["tags"],
                description=p["description"],
                open_hours=p.get("open_hours", ""),
                source="venue",
                score=p["rating"],
            )
            for p in resp.data.get("pois", [])
        ]

    def _search_outdoor_parks(self) -> List[Candidate]:
        """搜索户外公园（免费亲子）"""
        resp = api.location_nearby_search(
            keywords=["公园", "户外", "绿地", "游乐场"],
            lat=self.home_lat,
            lng=self.home_lng,
            radius_km=5.0,
        )
        if resp.code != 0:
            return []
        return [
            Candidate(
                id=p["id"],
                name=p["name"],
                category=p["category"],
                location=p["location"],
                rating=p["rating"],
                price=p["price"],
                tags=p["tags"],
                description=p["description"],
                open_hours=p.get("open_hours", ""),
                source="venue",
                score=p["rating"] * 0.8,  # 户外公园权重略低
            )
            for p in resp.data.get("pois", [])
        ]

    def _search_family_restaurants(self) -> List[Candidate]:
        """搜索家庭餐厅（考虑减肥）"""
        cuisine = None
        if self.intent.wife_dieting:
            cuisine = "轻食沙拉"

        resp = api.restaurant_search(
            cuisine=cuisine,
            lat=self.home_lat,
            lng=self.home_lng,
            radius_km=3.0,
            max_avg_price=200.0,
            require_availability=True,
        )
        if resp.code != 0:
            return []
        return [
            Candidate(
                id=r["id"],
                name=r["name"],
                category=r["cuisine"],
                location=r["location"],
                rating=r["rating"],
                price=r["avg_price"],
                tags=r["tags"],
                description=r["description"],
                source="restaurant",
                score=r["rating"] + 0.5 if r["has_availability"] else r["rating"] - 1.0,
            )
            for r in resp.data.get("restaurants", [])
        ]

    def _search_friend_activities(self) -> List[Candidate]:
        """搜索朋友聚会活动"""
        resp = api.location_nearby_search(
            keywords=["展览", "密室", "运动", "KTV", "游乐"],
            lat=self.home_lat,
            lng=self.home_lng,
            radius_km=5.0,
        )
        if resp.code != 0:
            return []
        return [
            Candidate(
                id=p["id"],
                name=p["name"],
                category=p["category"],
                location=p["location"],
                rating=p["rating"],
                price=p["price"],
                tags=p["tags"],
                description=p["description"],
                open_hours=p.get("open_hours", ""),
                source="activity",
                score=p["rating"] + 0.3,  # 活动加权
            )
            for p in resp.data.get("pois", [])
        ]

    def _search_friend_restaurants(self) -> List[Candidate]:
        """搜索朋友聚餐餐厅"""
        resp = api.restaurant_search(
            lat=self.home_lat,
            lng=self.home_lng,
            radius_km=3.0,
            max_avg_price=200.0,
            require_availability=True,
        )
        if resp.code != 0:
            return []
        return [
            Candidate(
                id=r["id"],
                name=r["name"],
                category=r["cuisine"],
                location=r["location"],
                rating=r["rating"],
                price=r["avg_price"],
                tags=r["tags"],
                description=r["description"],
                source="restaurant",
                score=r["rating"] + 0.5 if r["has_availability"] else r["rating"] - 1.0,
            )
            for r in resp.data.get("restaurants", [])
        ]


def rank_candidates(candidates: List[Candidate], top_n: int = 5) -> List[Candidate]:
    """按综合评分排序，保留 top_n"""
    sorted_list = sorted(candidates, key=lambda c: c.score, reverse=True)
    return sorted_list[:top_n]
"""
Mock 数据 — 模拟美团 POI / 餐厅 / 活动数据
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, time

# ========== 通用数据结构 ==========

@dataclass
class Location:
    lat: float        # 纬度
    lng: float        # 经度
    name: str = ""   # 地名/地址

@dataclass
class POI:
    id: str
    name: str
    location: Location
    category: str          # e.g. "亲子乐园" / "展览" / "公园"
    rating: float = 0.0   # 评分 0-5
    price: float = 0.0    # avg_price/门票
    tags: List[str] = field(default_factory=list)
    description: str = ""
    open_hours: str = ""  # 营业时间


@dataclass
class Restaurant:
    id: str
    name: str
    location: Location
    cuisine: str           # 菜系
    avg_price: float = 0.0
    rating: float = 0.0
    tags: List[str] = field(default_factory=list)
    has_availability: bool = True   # 是否有位
    queue_time_min: Optional[int] = None  # 需要排队时长(分钟)
    seats: int = 0          # 可订座位数
    description: str = ""


@dataclass
class DeliveryItem:
    id: str
    name: str
    price: float
    shop_name: str


# ========== 模拟数据 ==========

MOCK_LOCATIONS = {
    "home": Location(lat=31.2304, lng=121.4737, name="上海市静安区某小区"),
    "park": Location(lat=31.2350, lng=121.4780, name="静安公园"),
    "mall": Location(lat=31.2320, lng=121.4750, name="静安大悦城"),
}

# 亲子/儿童友好景点/活动
MOCK_VENUES = [
    POI(
        id="v001", name="静安公园·儿童游乐区",
        location=MOCK_LOCATIONS["park"],
        category="户外公园", rating=4.5, price=0.0,
        tags=["户外", "免费", "滑梯", "沙坑"],
        description="开阔的绿化空间，有滑梯、秋千、攀爬架，适合5岁孩子户外活动"
    ),
    POI(
        id="v002", name="大悦城·奇宝王国",
        location=MOCK_LOCATIONS["mall"],
        category="亲子乐园", rating=4.7, price=68.0,
        tags=["室内", "海洋球", "积木", "5岁以下"],
        description="室内亲子乐园，海洋球池+积木区，限高1.4m以下儿童"
    ),
    POI(
        id="v003", name="上海自然博物馆",
        location=Location(lat=31.2200, lng=121.4800, name="静安区山海关路399号"),
        category="博物馆", rating=4.8, price=0.0,
        tags=["科普", "亲子", "免费预约"],
        description="需提前在美团预约，恐龙化石+活体展区，孩子可触摸互动"
    ),
    POI(
        id="v004", name="乐高探索中心",
        location=Location(lat=31.2400, lng=121.4700, name="普陀区近铁广场"),
        category="亲子乐园", rating=4.6, price=139.0,
        tags=["室内", "乐高", "4D影院"],
        description="大型乐高室内游乐场，含得宝小镇+4D影院，建议提前购票"
    ),
]

# 朋友聚会活动
MOCK_FRIEND_ACTIVITIES = [
    POI(
        id="a001", name="teamLab无界艺术展",
        location=Location(lat=31.2180, lng=121.4820, name="黄浦区黄浦滨江"),
        category="展览", rating=4.9, price=198.0,
        tags=["艺术", "拍照", "沉浸式"],
        description="沉浸式数字艺术展，网红打卡地，需提前预约"
    ),
    POI(
        id="a002", name="静安公园·CityWalk小吃街",
        location=MOCK_LOCATIONS["park"],
        category="CityWalk", rating=4.3, price=0.0,
        tags=["散步", "小吃", "户外"],
        description="公园周边小吃市集，适合下午茶+散步，边吃边逛"
    ),
    POI(
        id="a003", name="XYZ密室逃脱",
        location=Location(lat=31.2330, lng=121.4760, name="静安区南京西路1038号"),
        category="密室", rating=4.7, price=128.0,
        tags=["解谜", "团队", "4人最佳"],
        description="4人组队最佳，推荐《星际穿越》主题，时长约90分钟"
    ),
    POI(
        id="a004", name="静安体育馆·羽毛球场地",
        location=Location(lat=31.2370, lng=121.4790, name="静安区体育中心"),
        category="运动", rating=4.4, price=40.0,
        tags=["运动", "室内", "4人双打"],
        description="室内羽毛球场地，4片半场，需提前预约球拍需自带"
    ),
]

# 餐厅数据
MOCK_RESTAURANTS = [
    Restaurant(
        id="r001", name="GreenSalad 轻食沙拉",
        location=Location(lat=31.2330, lng=121.4765, name="静安区南京西路1038号商场B1"),
        cuisine="轻食沙拉", avg_price=58.0, rating=4.6,
        tags=["轻食", "健康", "沙拉", "素食友好"],
        has_availability=True,
        description="新鲜沙拉+果饮，老婆减肥首选，提供儿童餐具"
    ),
    Restaurant(
        id="r002", name="粤江知味",
        location=Location(lat=31.2345, lng=121.4775, name="静安区北京西路123号"),
        cuisine="粤菜", avg_price=120.0, rating=4.7,
        tags=["粤菜", "点心", "儿童友好", "环境好"],
        has_availability=True, seats=8,
        description="广式点心+粤菜，儿童有专属餐具和餐椅，需提前订座"
    ),
    Restaurant(
        id="r003", name="海底捞火锅",
        location=Location(lat=31.2315, lng=121.4745, name="静安区西藏北路198号大悦城6楼"),
        cuisine="火锅", avg_price=150.0, rating=4.5,
        tags=["火锅", "服务好", "等位区"],
        has_availability=False, queue_time_min=45,
        description="等位时间约45分钟起，建议提前取号或错峰前往"
    ),
    Restaurant(
        id="r004", name="西堤牛排",
        location=Location(lat=31.2325, lng=121.4780, name="静安区南京西路1266号恒隆广场4楼"),
        cuisine="西餐", avg_price=200.0, rating=4.8,
        tags=["牛排", "约会", "儿童友好"],
        has_availability=True, seats=10,
        description="环境优雅，适合家庭聚餐，牛排+意面+儿童套餐"
    ),
    Restaurant(
        id="r005", name="鹿港小镇",
        location=Location(lat=31.2340, lng=121.4760, name="静安区南京西路819号"),
        cuisine="台菜", avg_price=80.0, rating=4.4,
        tags=["台菜", "性价比", "聚餐"],
        has_availability=True, seats=12,
        description="4人聚餐首选，性价比高，菜品丰富不踩雷"
    ),
]

# 配送商品（蛋糕/鲜花）
MOCK_DELIVERY_ITEMS = [
    DeliveryItem(id="d001", name="6寸草莓鲜奶蛋糕", price=168.0, shop_name="好利来"),
    DeliveryItem(id="d002", name="11朵红玫瑰鲜花束", price=158.0, shop_name="野兽派"),
    DeliveryItem(id="d003", name="4层迷你 cupcake 套装", price=128.0, shop_name="Lady M"),
    DeliveryItem(id="d004", name="手工曲奇礼盒", price=88.0, shop_name="Godiva"),
]
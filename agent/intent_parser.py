"""
意图解析器 — 从自然语言提取关键参数
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class UserIntent:
    """用户意图结构化结果"""
    # 原始输入
    raw_input: str = ""       # 原始用户消息

    # 场景类型
    scene: str = ""           # "family" / "friends" / "couple" / "solo"

    # 时间
    date: str = ""            # "YYYY-MM-DD"
    duration_hours: float = 4.0  # 活动时长（小时）

    # 地点偏好
    location: str = ""        # "附近"/"离家近" 等描述
    home_lat: float = 31.2304
    home_lng: float = 121.4737

    # 家庭场景属性
    has_child: bool = False
    child_age: Optional[int] = None
    wife_dieting: bool = False

    # 朋友场景属性
    group_size: int = 4
    group_male: int = 2
    group_female: int = 2

    # 额外需求
    needs_delivery: bool = False  # 蛋糕/鲜花
    delivery_item: str = ""


def parse_intent(message: str) -> UserIntent:
    """
    将用户输入的自然语言解析为结构化意图
    这是 Mock 实现，基于关键词匹配
    """
    msg = message.strip()
    intent = UserIntent()
    intent.raw_input = message.strip()

    # 检测场景
    # 注意：分支顺序很重要。
    #   1) family 必须先判，"和老婆孩子" 属于家庭场景；
    #   2) couple 必须在 friends 之前判，否则 "女朋友" 里的 "朋友" 会被 friends 误命中；
    #   3) friends 兜底群体场景；4) solo 兜底单人。
    is_couple_kw = ("女朋友" in msg or "男朋友" in msg or "女友" in msg
                    or "男友" in msg or "情侣" in msg or "约会" in msg
                    or "对象" in msg)
    is_family_kw = ("孩子" in msg or "小孩" in msg or "家庭" in msg or "亲子" in msg
                    or ("老婆" in msg and not is_couple_kw))

    if is_family_kw:
        intent.scene = "family"
        intent.has_child = True
        # 提取孩子年龄
        age_match = re.search(r"(\d+)[岁個月]", msg)
        if age_match:
            intent.child_age = int(age_match.group(1))
        else:
            intent.child_age = 5  # 默认5岁（题目给定的）
        if "老婆" in msg and ("减肥" in msg or "瘦身" in msg or "健康" in msg):
            intent.wife_dieting = True
    elif is_couple_kw:
        intent.scene = "couple"
        intent.group_size = 2
    elif "朋友" in msg or "聚会" in msg or "闺蜜" in msg or "兄弟" in msg:
        intent.scene = "friends"
        # 提取人数
        people_match = re.search(r"(\d+)[个人]", msg)
        if people_match:
            intent.group_size = int(people_match.group(1))
        # 提取男女比例
        male_match = re.search(r"(\d+)个?(男生|男|兄弟|男同胞)", msg)
        female_match = re.search(r"(\d+)个?(女生|女|闺蜜|女同胞)", msg)
        if male_match:
            intent.group_male = int(male_match.group(1))
        if female_match:
            intent.group_female = int(female_match.group(1))
    else:
        intent.scene = "solo"

    # 检测时间
    if "今天下午" in msg or "今天" in msg and "下午" in msg:
        intent.date = "2026-06-04"
        intent.duration_hours = 4.0
    elif "明天" in msg:
        intent.date = "2026-06-05"
    elif "周末" in msg:
        intent.date = "2026-06-06"

    # 检测地点偏好
    if "别太远" in msg or "附近" in msg or "离家近" in msg or "近一点" in msg:
        intent.location = "nearby"

    # 检测配送需求
    if "蛋糕" in msg or "鲜花" in msg or "花" in msg:
        intent.needs_delivery = True
        if "蛋糕" in msg:
            intent.delivery_item = "cake"
        elif "鲜花" in msg or "花束" in msg:
            intent.delivery_item = "flowers"

    return intent


def build_explore_prompt(intent: UserIntent) -> str:
    """根据意图构建探索查询"""
    if intent.scene == "family":
        return (
            f"家庭亲子游，孩子{intent.child_age}岁，"
            f"{'老婆在减肥，' if intent.wife_dieting else ''}"
            f"在{intent.location or '家附近'}找适合全家参与的活动"
        )
    elif intent.scene == "friends":
        return (
            f"朋友{int(intent.group_size)}人聚会（{intent.group_male}男{int(intent.group_female)}女），"
            f"在{intent.location or '家附近'}找有趣的活动"
        )
    return ""
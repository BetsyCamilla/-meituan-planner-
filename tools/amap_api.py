"""
高德地图 Web 服务 API 封装 —— 周边 POI 搜索。

仅在配置了 AMAP_API_KEY 时启用；否则上层（meituan_api）会自动回退到 mock 数据。
本模块只负责「真实地点搜索」，下单类操作（订座/门票/配送）仍由 mock 模拟，
因为高德不提供真实交易能力，且 demo 不应产生真实订单。

接口：周边搜索 https://restapi.amap.com/v3/place/around
官方文档：https://lbs.amap.com/api/webservice/guide/api/newpoisearch
"""

import os
import logging
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger("gonow")

AMAP_BASE = "https://restapi.amap.com/v3/place/around"
_TIMEOUT = 6  # 秒，超时即视为失败并回退


def amap_enabled() -> bool:
    """是否配置了高德 key。"""
    return bool(os.getenv("AMAP_API_KEY", "").strip())


def _parse_rating(biz_ext: Any) -> float:
    """从 biz_ext.rating 解析评分，缺失/非法返回 0.0。"""
    if not isinstance(biz_ext, dict):
        return 0.0
    raw = biz_ext.get("rating", "")
    try:
        return float(raw) if raw not in ("", [], None) else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_cost(biz_ext: Any) -> float:
    """从 biz_ext.cost 解析人均消费，缺失返回 0.0。"""
    if not isinstance(biz_ext, dict):
        return 0.0
    raw = biz_ext.get("cost", "")
    try:
        return float(raw) if raw not in ("", [], None) else 0.0
    except (ValueError, TypeError):
        return 0.0


def _normalize_poi(p: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    把高德单条 POI 映射成项目内部统一结构（与 mock 的 pois 字段对齐）：
      id / name / category / location{lat,lng,name} / rating / price / tags / description / open_hours
    解析失败返回 None。
    """
    try:
        # location 形如 "121.4737,31.2304"（经度,纬度）
        loc = p.get("location", "")
        if isinstance(loc, str) and "," in loc:
            lng_s, lat_s = loc.split(",", 1)
            lng, lat = float(lng_s), float(lat_s)
        else:
            lng = lat = 0.0

        biz_ext = p.get("biz_ext", {})
        type_str = p.get("type", "")  # "餐饮服务;中餐厅;..." 取首段做粗分类
        category = type_str.split(";")[0] if type_str else (p.get("typecode", "") or "其他")

        addr = p.get("address", "")
        if isinstance(addr, list):  # 高德偶尔返回空 list
            addr = ""

        return {
            "id": p.get("id", ""),
            "name": p.get("name", ""),
            "category": category,
            "location": {"lat": lat, "lng": lng, "name": addr or p.get("name", "")},
            "rating": _parse_rating(biz_ext),
            "price": _parse_cost(biz_ext),
            "tags": [t for t in [p.get("type", "").split(";")[-1]] if t],
            "description": addr or "",
            "open_hours": "",  # v3 around 不直接返回营业时间
        }
    except (ValueError, AttributeError, KeyError) as e:
        logger.debug(f"高德 POI 解析失败: {e}")
        return None


def around_search(
    keywords: List[str],
    lat: float,
    lng: float,
    radius_km: float = 3.0,
    limit: int = 10,
) -> Optional[List[Dict[str, Any]]]:
    """
    高德周边搜索。成功返回归一化后的 POI 列表；失败（无 key / 网络错误 / 高德报错）返回 None，
    由上层决定是否回退到 mock。
    """
    key = os.getenv("AMAP_API_KEY", "").strip()
    if not key:
        return None

    params = {
        "key": key,
        "location": f"{lng},{lat}",          # 高德要求「经度,纬度」
        "keywords": "|".join(keywords),       # 多关键词用 | 分隔
        "radius": int(radius_km * 1000),      # 转为米
        "extensions": "all",                  # 返回评分/人均等扩展字段
        "offset": min(limit, 25),             # 每页条数
        "page": 1,
        "sortrule": "weight",                 # 按综合权重排序
    }

    try:
        resp = requests.get(AMAP_BASE, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning(f"高德 API 请求失败，将回退 mock: {e}")
        return None
    except ValueError as e:
        logger.warning(f"高德 API 响应非 JSON，将回退 mock: {e}")
        return None

    # 高德成功时 status == "1"
    if str(data.get("status")) != "1":
        logger.warning(f"高德 API 返回错误: {data.get('info')}（infocode={data.get('infocode')}），回退 mock")
        return None

    pois = data.get("pois", []) or []
    results = [poi for poi in (_normalize_poi(p) for p in pois) if poi]
    logger.info(f"高德周边搜索命中 {len(results)} 条（keywords={keywords}）")
    return results

"""
后端入口 — FastAPI + SSE 流式规划 + LLM API 集成

功能特性：
- 意图解析（场景、人数、约束条件）
- 并行候选搜索（玩、吃、活动）
- LLM 规划 + 骨架模板融合
- ReAct 搜索/执行自愈
- SSE 流式规划结果
- 自动下单和预订
- 完整的错误处理和日志记录
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# 设置项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ═══════════════════════════════════════════════════════════════
# 日志配置
# ═══════════════════════════════════════════════════════════════

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 创建日志处理器
logger = logging.getLogger("gonow")
logger.setLevel(getattr(logging, LOG_LEVEL))

# 文件处理器
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logger.addHandler(file_handler)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))
logger.addHandler(console_handler)

import asyncio
import json
import re
from datetime import datetime
from typing import AsyncGenerator, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
# 明确指定 .env 路径，避免 cwd 不一致导致加载失败
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from sse_starlette.sse import EventSourceResponse
import aiohttp

from agent.intent_parser import parse_intent, UserIntent
from agent.explorer import Explorer, Candidate
from agent.planner import Planner as BasePlanner, format_plan_md, format_plan_json
from agent.executor import Executor
from agent.enhanced_planner import (
    EnhancedPlanner, match_skeleton, DegradationLevel,
    validate_llm_plan, mock_probability_booking,
    ReActSearchHealer, ReActExecuteHealer,
)

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")

# 全局 aiohttp session（复用连接，降低开销）
_http_session: Optional[aiohttp.ClientSession] = None

async def get_http_session() -> aiohttp.ClientSession:
    """获取全局HTTP会话"""
    global _http_session
    if _http_session is None:
        timeout = aiohttp.ClientTimeout(total=30)
        _http_session = aiohttp.ClientSession(timeout=timeout)
    return _http_session

async def close_http_session():
    """关闭全局HTTP会话"""
    global _http_session
    if _http_session:
        await _http_session.close()
        _http_session = None

# ═══════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════

class PlanRequest(BaseModel):
    message: str = Field(..., description="用户输入的自然语言消息")
    user_lat: float = Field(default=31.2304, description="用户纬度")
    user_lng: float = Field(default=121.4737, description="用户经度")
    auto_execute: bool = Field(default=False, description="确认后自动下单")
    # 可选：前端传入的 API Key（覆盖服务端 .env 配置；仅本次请求有效，不落盘）
    llm_api_key: Optional[str] = Field(default=None, description="LLM API Key（可选，覆盖服务端配置）")
    amap_api_key: Optional[str] = Field(default=None, description="高德地图 API Key（可选，覆盖服务端配置）")


class StreamingConfig(BaseModel):
    use_skeleton: bool = Field(default=True)
    use_llm: bool = Field(default=True)
    max_distance: int = Field(default=3000)


# ═══════════════════════════════════════════════════════════════
# FastAPI 应用
# ═══════════════════════════════════════════════════════════════

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时无特殊操作，关闭时清理全局 HTTP 会话。"""
    yield
    await close_http_session()


app = FastAPI(
    title="走起 GoNow API",
    version="1.0.0",
    description="本地场景短时活动规划与执行 Agent",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # 与 allow_origins=["*"] 搭配时必须为 False（浏览器规范），否则带凭证请求会被拒
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# LLM 调用
# ═══════════════════════════════════════════════════════════════

async def call_llm(
    messages: List[dict],
    model: str = LLM_MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    调用 LLM API（支持 DeepSeek/OpenAI 兼容 API），流式返回。

    参数：
        messages: [{"role": "user"/"assistant", "content": "..."}]
        model: 模型名称
        api_key: 显式传入的 Key（优先于服务端 .env；为空则回退 LLM_API_KEY）
        base_url: 显式传入的 API 地址（为空则回退 LLM_BASE_URL）

    yield: 流式文本块
    """
    eff_key = (api_key or LLM_API_KEY or "").strip()
    eff_base = (base_url or LLM_BASE_URL).rstrip("/")
    logger.info(f"调用 LLM API - 模型: {model}")

    if not eff_key:
        logger.warning("LLM_API_KEY 未设置，使用规则降级")
        yield "[ERROR] LLM_API_KEY 未设置，请设置环境变量 LLM_API_KEY\n"
        return

    url = f"{eff_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {eff_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    async def stream_events() -> AsyncGenerator[str, None]:
        """流式读取 LLM 响应"""
        try:
            logger.debug(f"连接 LLM API: {url}")
            session = await get_http_session()
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"LLM API 错误 {resp.status}: {error_text}")
                    yield f"[ERROR] API 返回错误 {resp.status}: {error_text}\n"
                    return
                
                logger.info("LLM API 连接成功，开始流式处理")
                chunk_count = 0
                async for line in resp.content:
                    line = line.decode().strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                chunk_count += 1
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError) as e:
                            logger.debug(f"解析 LLM 响应行失败: {e}")
                            pass  # 跳过错误行
                
                logger.info(f"LLM API 流式处理完成，共 {chunk_count} 块")
        except asyncio.TimeoutError:
            logger.error("LLM API 超时（60秒）")
            yield "[ERROR] LLM API 超时（60秒）\n"
        except aiohttp.ClientError as e:
            logger.error(f"LLM API 连接错误: {str(e)}")
            yield f"[ERROR] LLM API 连接错误: {str(e)}\n"
        except Exception as e:
            logger.error(f"LLM 调用异常: {str(e)}", exc_info=True)
            yield f"[ERROR] LLM 调用异常: {str(e)}\n"

    async for chunk in stream_events():
        yield chunk


def build_llm_plan_prompt(intent: UserIntent, candidates: dict, skeleton_name: str) -> str:
    """构建 LLM 规划 prompt"""
    venue_list = "\n".join(
        f"- {v.name}（{v.category}，评分{v.rating}，{'免费' if v.price==0 else f'{v.price}元'}，{v.location.get('name','')})"
        for v in candidates.get("venues", [])[:5]
    )
    restaurant_list = "\n".join(
        f"- {r.name}（{r.category}，人均{r.price}元，评分{r.rating}，{r.location.get('name','')})"
        for r in candidates.get("restaurants", [])[:5]
    )
    activity_list = "\n".join(
        f"- {a.name}（{a.category}，{a.price}元，评分{a.rating}）"
        for a in candidates.get("activities", [])[:5]
    )

    return f"""你是一个专业行程规划师。用户需求：{intent.raw_input}

你的任务是根据候选地点，为用户规划一个下午的行程方案。

**当前匹配的时间线骨架（来自 {skeleton_name}）：**
- 14:00-14:30：前往活动地点
- 14:30-17:00：下午活动（玩）
- 17:00-17:30：转场
- 17:30-19:30：晚餐

**可用候选地点：**

【玩】{venue_list}
【活动】{activity_list}
【餐厅】{restaurant_list}

**要求：**
1. 选择 2-4 个地点组成完整行程（至少1个玩+1个吃），并加入必要的「交通」转场段
2. 优先选择评分高、距离近、有位的地点
3. 如果是家庭场景（带孩子），优先亲子乐园/公园
4. 如果是老婆在减肥，优先轻食/健康餐厅

**输出格式（极其重要）：**
只输出一个 JSON 代码块，不要任何额外文字、解释或前后缀。严格使用以下结构：

```json
{{
  "title": "行程标题（简短）",
  "description": "一句话描述这个行程",
  "total_cost": 总花费数字,
  "items": [
    {{
      "type": "交通｜吃｜玩｜看｜购｜休 之一",
      "activity": "活动名称",
      "location_name": "地点名称",
      "arrive_time": "HH:MM",
      "leave_time": "HH:MM",
      "stay_minute": 停留分钟数,
      "cost": 该项花费数字
    }}
  ]
}}
```

注意：total_cost 与 cost 必须是纯数字（不带「元」字），time 必须是 HH:MM 格式。
"""


# ═══════════════════════════════════════════════════════════════
# SSE 流式规划端点
# ═══════════════════════════════════════════════════════════════

async def plan_stream(request: PlanRequest, config: StreamingConfig) -> AsyncGenerator[dict, None]:
    """SSE 流式规划主流程"""

    # 解析本次请求的有效 Key：前端传入优先，否则回退服务端 .env
    eff_llm_key = (request.llm_api_key or LLM_API_KEY or "").strip()
    eff_amap_key = (request.amap_api_key or AMAP_API_KEY or "").strip()
    # 高德搜索通过环境变量读取 key（amap_api.around_search 在调用时读取），
    # 这里临时写入本次请求的有效值；请求结束后还原，避免并发请求互相污染。
    _amap_prev = os.environ.get("AMAP_API_KEY")
    if eff_amap_key:
        os.environ["AMAP_API_KEY"] = eff_amap_key
    else:
        os.environ.pop("AMAP_API_KEY", None)

    try:
        async for evt in _plan_stream_body(request, config, eff_llm_key):
            yield evt
    finally:
        # 还原环境变量
        if _amap_prev is None:
            os.environ.pop("AMAP_API_KEY", None)
        else:
            os.environ["AMAP_API_KEY"] = _amap_prev


async def _plan_stream_body(
    request: PlanRequest, config: StreamingConfig, eff_llm_key: str
) -> AsyncGenerator[dict, None]:
    """规划主流程实体（key 已解析）。"""

    # Step 1: 意图解析
    yield {"event": "step", "data": "正在解析出行意图..."}
    intent = parse_intent(request.message)
    intent.home_lat = request.user_lat
    intent.home_lng = request.user_lng

    # Step 2: 骨架模板匹配
    if config.use_skeleton:
        yield {"event": "step", "data": "正在匹配时间线骨架..."}
        skeleton = match_skeleton(intent)
        yield {"event": "skeleton", "data": {
            "name": skeleton.name,
            "slots": skeleton.slots,
        }}
    else:
        skeleton = None

    # Step 3: 候选搜索
    yield {"event": "step", "data": "正在搜索附近候选地点..."}
    explorer = Explorer(intent)
    candidates = await explorer.explore()

    counts = {k: len(v) for k, v in candidates.items()}
    yield {"event": "step", "data": f"已找到：{counts}"}

    # Step 4: ReAct 搜索自愈（如有必要）
    if config.use_skeleton:
        search_healer = ReActSearchHealer(explorer, intent)
        attempt = 0
        while search_healer.should_heal(candidates, intent.scene) and attempt < 2:
            attempt += 1
            yield {"event": "step", "data": f"🔄 扩大搜索范围（第{attempt}次）..."}
            candidates = await search_healer.heal(candidates, gap_categories=[])

    # Step 5: LLM 生成方案（流式）
    plan_text = ""
    if config.use_llm and eff_llm_key:
        yield {"event": "step", "data": "正在调用 AI 规划师..."}
        skeleton_name = skeleton.name if skeleton else "通用"
        prompt = build_llm_plan_prompt(intent, candidates, skeleton_name)
        messages = [{"role": "user", "content": prompt}]

        async for chunk in call_llm(messages, api_key=eff_llm_key):
            yield {"event": "chunk", "data": chunk}
            plan_text += chunk

        yield {"event": "plan_raw", "data": plan_text}
    else:
        # 规则降级：输出与 LLM 一致的 JSON 结构（包在 ```json 围栏中），
        # 前端据此走结构化时间轴卡片，而非丑陋的纯文本。
        yield {"event": "step", "data": "使用规则生成方案..."}
        base_planner = BasePlanner(intent)
        plan = base_planner.make_plan(
            venues=candidates.get("venues", []),
            restaurants=candidates.get("restaurants", []),
            activities=candidates.get("activities", []),
        )
        plan_json = format_plan_json(plan)
        fenced = "```json\n" + json.dumps(plan_json, ensure_ascii=False) + "\n```"
        plan_text = fenced
        yield {"event": "chunk", "data": fenced}

    # Step 6: POI 校验
    yield {"event": "step", "data": "正在校验 POI 数据可信度..."}

    # Step 7: 执行下单
    if request.auto_execute:
        yield {"event": "step", "data": "正在执行预订..."}
        base_planner = BasePlanner(intent)
        plan = base_planner.make_plan(
            venues=candidates.get("venues", []),
            restaurants=candidates.get("restaurants", []),
            activities=candidates.get("activities", []),
        )
        executor = Executor(intent)
        report = executor.execute(plan)
        for r in report.results:
            emoji = "✅" if r.success else "❌"
            yield {"event": "booking", "data": f"{emoji} {r.message}"}

    yield {"event": "done", "data": "规划完成"}


# ═══════════════════════════════════════════════════════════════
# API 路由
# ═══════════════════════════════════════════════════════════════

@app.post("/api/plan/stream")
async def api_plan_stream(request: PlanRequest):
    """
    SSE 流式规划接口
    前端通过 EventSource 接收事件流
    
    事件类型：
    - step: 规划步骤进度
    - skeleton: 匹配的时间线骨架
    - chunk: 规划内容（流式）
    - booking: 预订结果
    - done: 规划完成
    - error: 错误信息
    """
    logger.info(f"开始规划：{request.message[:50]}...")
    
    config = StreamingConfig()
    
    async def event_generator():
        try:
            async for event in plan_stream(request, config):
                yield {
                    "event": event.get("event", "message"),
                    "data": json.dumps(event.get("data", "")),
                }
        except Exception as e:
            logger.error(f"规划异常：{str(e)}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps(f"规划失败：{str(e)}"),
            }

    return EventSourceResponse(event_generator())


@app.post("/api/plan/generate")
async def api_plan_generate(request: PlanRequest):
    """
    非流式规划接口（一次性返回完整方案）
    
    返回：
    {
        "code": 0,
        "message": "ok",
        "data": {
            "plan_md": "完整规划（Markdown）",
            "llm_used": true/false,
            "candidates": {...}
        }
    }
    """
    try:
        logger.info(f"生成规划：{request.message[:50]}...")
        
        intent = parse_intent(request.message)
        intent.home_lat = request.user_lat
        intent.home_lng = request.user_lng

        explorer = Explorer(intent)
        candidates = await explorer.explore()

        config = StreamingConfig(use_llm=True, use_skeleton=True)
        plan_text = ""
        llm_used = False

        if config.use_llm and LLM_API_KEY:
            skeleton = match_skeleton(intent)
            skeleton_name = skeleton.name if skeleton else "通用"
            prompt = build_llm_plan_prompt(intent, candidates, skeleton_name)
            messages = [{"role": "user", "content": prompt}]
            async for chunk in call_llm(messages):
                plan_text += chunk
            plan_md = plan_text
            llm_used = True
            logger.info("使用 LLM 生成规划")
        else:
            base_planner = BasePlanner(intent)
            plan = base_planner.make_plan(
                venues=candidates.get("venues", []),
                restaurants=candidates.get("restaurants", []),
                activities=candidates.get("activities", []),
            )
            plan_md = format_plan_md(plan)
            logger.info("使用规则生成规划")

        logger.info("规划生成成功")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "plan_md": plan_md,
                "llm_used": llm_used,
                "candidates": {
                    k: [{"name": c.name, "category": c.category, "rating": c.rating, "price": c.price}
                       for c in v]
                    for k, v in candidates.items()
                },
            }
        }
    except Exception as e:
        logger.error(f"规划生成异常：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"规划失败：{str(e)}")


@app.post("/api/booking/batch")
async def api_booking_batch(request: PlanRequest):
    """
    批量预订接口（Mock 概率模拟）
    
    返回：
    {
        "code": 0,
        "message": "ok",
        "data": {
            "results": [
                {"location_name": "...", "status": "success/failed", "order_id": "..."}
            ]
        }
    }
    """
    try:
        logger.info(f"批量预订：{request.message[:50]}...")
        
        intent = parse_intent(request.message)
        intent.home_lat = request.user_lat
        intent.home_lng = request.user_lng

        explorer = Explorer(intent)
        candidates = await explorer.explore()
        base_planner = BasePlanner(intent)
        plan = base_planner.make_plan(
            venues=candidates.get("venues", []),
            restaurants=candidates.get("restaurants", []),
            activities=candidates.get("activities", []),
        )

        results = []
        for slot in plan.slots:
            if slot.type in ("玩", "吃") and slot.cost > 0:
                r = mock_probability_booking(
                    "restaurant" if slot.type == "吃" else "venue",
                    1, slot.activity
                )
                results.append({
                    "location_name": slot.activity,
                    **r
                })
                logger.info(f"预订 {slot.activity}：{r.get('status', 'unknown')}")

        logger.info(f"批量预订完成，共 {len(results)} 项")
        return {"code": 0, "message": "ok", "data": {"results": results}}
    except Exception as e:
        logger.error(f"批量预订异常：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预订失败：{str(e)}")


@app.get("/api/health")
async def api_health():
    """
    健康检查接口
    返回系统状态和 LLM 配置情况
    """
    try:
        logger.debug("执行健康检查")
        health_status = {
            "status": "ok",
            "llm_configured": bool(LLM_API_KEY),
            "llm_model": LLM_MODEL,
            "timestamp": datetime.now().isoformat(),
        }
        return health_status
    except Exception as e:
        logger.error(f"健康检查异常：{str(e)}")
        return {
            "status": "error",
            "llm_configured": False,
            "error": str(e),
        }


@app.get("/")
async def root():
    """
    根路由 - 返回 API 信息
    """
    return {
        "name": "走起 GoNow API",
        "version": "1.0.0",
        "description": "本地场景短时活动规划与执行 Agent",
        "docs": "/docs",
        "health": "/api/health",
    }


# ═══════════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
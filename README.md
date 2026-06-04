# 🗺️ 走起 GoNow

> 一句话，搞定一下午的行程。

「走起」是一个**本地场景短时活动规划 Agent**：你用自然语言描述出行场景（带孩子 / 朋友聚会 / 约会 / 独自放松），它自动解析意图、搜索附近候选地点、生成带时间轴的行程方案，并支持一键预订。

融合了**时间线骨架模板** + **ReAct 自愈** + **多级降级**三大机制，即使在断网、无 API Key、服务超时等异常情况下也能稳定产出方案。

<p>
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-orange.svg" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9+-blue.svg" />
  <img alt="React" src="https://img.shields.io/badge/React-18-61dafb.svg" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.104+-009688.svg" />
</p>



https://github.com/user-attachments/assets/0145d6dc-cf01-476c-96ce-20b139930c75



---

## ✨ 核心特性

| 功能 | 说明 |
|------|------|
| 🧠 自然语言意图解析 | 从一句话识别场景、人数、孩子年龄、是否减肥、配送需求等 |
| 🔍 真实地点搜索 | 配置高德 Key 后使用真实 POI；未配置自动回退内置 mock 数据 |
| 🗓️ 骨架模板规划 | 预置时间线模板（伙伴 × 天气 × 时段），毫秒级响应 |
| 🤖 LLM 智能编排 | 接入 DeepSeek / OpenAI 兼容 API，生成自然的行程方案 |
| 🔧 ReAct 自愈 | 候选不足自动放宽搜索；预订失败自动找同类替代 |
| 🛡️ 多级降级 | 真实数据→mock / LLM→规则 / 卡片→纯文本，任一环节失效都不崩 |
| ⚡ SSE 流式 | 前端实时展示规划进度与方案生成过程 |
| 🎨 现代化 UI | 浅色清爽设计，行程时间轴卡片可视化 |

---

## 🚀 快速开始

> 前置：Python 3.9+、Node.js 18+。首次运行可先执行 `python check_env.py` 检查依赖。

### 一键启动（推荐）

```bash
# Windows：双击 start_all.bat
# Mac / Linux：
python start_all.py
```

启动后访问 **http://localhost:5173** 。

### 分别启动

```bash
# 后端
cd backend
cp .env.example .env          # 可选：填入 API Key（不填也能运行）
pip install -r requirements.txt
python -m uvicorn server:app --reload --port 8000

# 前端（另开终端）
cd web
npm install
npm run dev
```

### 纯命令行演示（无需前端）

```bash
python main.py "今天下午是空的，想和老婆孩子出去玩几个小时，别离家太远，帮我安排一下"
```

---

## 🔑 配置 API Key（两种方式，均可选）

「走起」**不配置任何 Key 也能完整运行**（走内置 mock 数据 + 规则生成）。
想要更真实的体验，可配置以下 Key：

| Key | 作用 | 不配置时 |
|-----|------|---------|
| `LLM_API_KEY` | 接入 DeepSeek 等生成更自然的行程 | 走规则生成 |
| `AMAP_API_KEY` | 高德 Web 服务，搜索真实地点 POI | 走内置 mock 地点 |

**方式一：服务端配置**——复制 `backend/.env.example` 为 `backend/.env` 填入。

**方式二：网页内填写**——打开前端，点右上角「设置」，填入 Key（仅存浏览器内存，刷新即清空，不上传、不落盘）。

> 💡 高德 Key 请申请 **「Web 服务」** 类型（非 JS/Android/iOS），否则 HTTP 接口无法调用。
> 申请地址：https://lbs.amap.com/

---

## 📂 项目结构

```
GoNow/
├── agent/                     # 核心规划模块
│   ├── intent_parser.py       # 意图解析（family / friends / couple / solo）
│   ├── explorer.py            # 并行候选搜索（asyncio.gather）
│   ├── planner.py             # 时间轴规划 + 预算计算 + JSON 输出
│   ├── executor.py            # 自动下单 + 备选 fallback
│   └── enhanced_planner.py    # 融合增强版（骨架 / ReAct 自愈 / 降级 / 概率预订）
├── tools/
│   ├── mock_data.py           # 内置 mock POI / 餐厅 / 配送数据
│   ├── meituan_api.py         # 搜索 / 订座 / 门票 / 配送接口
│   └── amap_api.py            # 高德真实 POI 搜索封装
├── backend/
│   ├── server.py              # FastAPI + SSE 流式 + LLM 集成
│   ├── requirements.txt
│   └── .env.example           # 环境变量模板
├── web/                       # React + Tailwind 前端
├── main.py                    # CLI 入口
├── start_all.py / .bat        # 一键启动前后端
├── Dockerfile / docker-compose.yml
├── THIRD_PARTY.md             # 第三方设计致谢
├── LICENSE                    # MIT
└── README.md
```

---

## 🔌 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/plan/stream` | POST | SSE 流式规划（事件：step / skeleton / chunk / booking / done / error） |
| `/api/plan/generate` | POST | 非流式一次性规划 |
| `/api/booking/batch` | POST | 批量概率预订模拟 |
| `/api/health` | GET | 健康检查 + LLM 状态 |

启动后端后，完整交互式 API 文档见 **http://localhost:8000/docs** 。

---

## 🐳 Docker 部署

```bash
docker compose up --build
```

详见 [DEPLOYMENT.md](DEPLOYMENT.md)。

---

## 🔒 安全说明

- 本仓库通过 `.gitignore` 排除 `.env`，**请勿将真实 API Key 提交进 Git**。
- 网页内填写的 Key 仅存于浏览器内存，不会上传服务器或写入磁盘。
- 若公开部署给不特定用户，请勿在前端硬编码自己的 Key——让访问者填写各自的 Key。

---

## 🤝 贡献

欢迎 issue 和 PR。提交前请确保：

1. 不包含任何真实密钥或个人数据；
2. 后端改动通过基本自测（`python main.py "..."` 能正常出方案）；
3. 前端改动通过 `npm run build`。

---

## 🙏 致谢

本项目的部分设计思路受其他项目启发（均为独立实现，非源码再分发），详见 [THIRD_PARTY.md](THIRD_PARTY.md)。

---

## 📄 许可证

[MIT](LICENSE) © nana

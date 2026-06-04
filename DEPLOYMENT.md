# 走起 GoNow 部署指南

## 系统要求

- **Python**: 3.8+
- **Node.js**: 16.0+
- **npm**: 8.0+
- **操作系统**: Windows / macOS / Linux
- **内存**: ≥ 4GB
- **磁盘**: ≥ 500MB

## 快速启动（一键部署）

### 方式 1: 自动启动脚本（推荐）

```bash
# Windows
cd meituan-planner
python start_all.py

# macOS / Linux
cd meituan-planner
python3 start_all.py
```

或者使用批处理文件：
```bash
cd meituan-planner
start_all.bat
```

这将自动启动：
- ✅ 前端（React + Vite） - http://localhost:5173
- ✅ 后端（FastAPI） - http://localhost:8000
- ✅ API 文档 - http://localhost:8000/docs

---

## 详细启动步骤

### 步骤 1: 环境检查

```bash
cd meituan-planner
python check_env.py
```

输出应包括：
```
✓ Python version: 3.9+
✓ Required packages: installed
✓ Node.js: installed
✓ npm: installed
```

### 步骤 2: 安装依赖

#### 后端依赖
```bash
cd backend
pip install -r requirements.txt
cd ..
```

#### 前端依赖
```bash
cd web
npm install
cd ..
```

### 步骤 3: 启动后端服务

```bash
# 方式 A: 直接运行
python start_server.py

# 方式 B: 使用 uvicorn 指定端口
uvicorn backend.server:app --reload --port 8000 --host 0.0.0.0
```

**预期输出：**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 步骤 4: 启动前端服务

在新终端窗口中：
```bash
cd web
npm run dev
```

**预期输出：**
```
  VITE v5.4.21  ready in 500 ms
  ➜  Local:   http://localhost:5173/
```

### 步骤 5: 访问应用

打开浏览器访问：
- **应用**: http://localhost:5173
- **API文档**: http://localhost:8000/docs
- **后端健康检查**: http://localhost:8000/api/health

---

## 命令行使用（无需前端）

### 快速测试
```bash
python test.py
```

这将运行两个测试场景：
1. 亲子活动规划
2. 朋友聚会规划

### 增强版演示（融合流程）
```bash
python enhanced_main.py
```

### CLI 规划
```bash
python main.py
```

---

## Docker 部署

### 构建镜像

```bash
docker build -t gonow:latest .
```

### 运行容器

```bash
docker run -p 8000:8000 -p 5173:5173 gonow:latest
```

---

## 环境配置

### LLM 配置（可选）

如果需要使用外部 LLM API，设置环境变量：

```bash
# OpenAI
export OPENAI_API_KEY=sk-...
export OPENAI_API_BASE=https://api.openai.com/v1

# 或其他 LLM
export LLM_API_KEY=your-key
export LLM_API_BASE=your-base-url
```

### 日志配置

设置日志级别：
```bash
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

---

## 故障排除

### 问题 1: 端口被占用

**错误信息:**
```
Address already in use
```

**解决方案:**
```bash
# 查找占用端口的进程
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# 杀死进程
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# 或使用不同端口
uvicorn backend.server:app --port 8001
```

### 问题 2: 依赖安装失败

**解决方案:**
```bash
# 清除缓存
pip cache purge
pip install --no-cache-dir -r backend/requirements.txt

# 或使用镜像源（中国）
pip install -i https://pypi.tsinghua.edu.cn/simple -r backend/requirements.txt
```

### 问题 3: Node 模块找不到

**解决方案:**
```bash
cd web
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

### 问题 4: CORS 错误

**确保后端 CORS 配置正确：**
```python
# backend/server.py 中应有
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 性能优化建议

### 前端优化
- 启用 Vite 预构建
- 使用代码分割
- 启用 gzip 压缩

### 后端优化
- 使用连接池
- 启用异步操作
- 配置合适的 worker 数量

```bash
uvicorn backend.server:app --workers 4 --loop uvloop
```

---

## 监控和日志

### 查看实时日志
```bash
# 后端日志
tail -f logs/app.log

# 前端构建日志
npm run dev 2>&1 | tee logs/frontend.log
```

### API 性能监控

访问 http://localhost:8000/docs 查看 API 性能指标

---

## 常见配置

### 改变前端端口
```bash
cd web
npm run dev -- --port 5174
```

### 改变后端端口
```bash
python start_server.py --port 8001
```

### 生产环境部署

```bash
# 前端
cd web
npm run build  # 生成 dist 目录

# 后端
gunicorn -w 4 -b 0.0.0.0:8000 backend.server:app
```

---

## 获取帮助

- 📖 查看 [README.md](README.md)
- 📋 查看 [SPEC.md](SPEC.md)
- 🚀 查看 [QUICKSTART.md](QUICKSTART.md)
- 🐛 检查日志文件获取错误详情

---

**最后更新**: 2026-06-04

# 🎯 快速开始 - 走起 GoNow

## 👉 最快的方式 (3 步)

### Windows 用户
1. 双击 `start_all.bat`
2. 等待后端启动（显示 "Application startup complete"）
3. 打开浏览器访问 http://localhost:5173

### Mac/Linux 用户
```bash
python start_all.py
```
然后打开 http://localhost:5173

---

## ✅ 首次启动检查清单

- [ ] Python 3.9+ 已安装
- [ ] Node.js 已安装
- [ ] `backend/.env` 已配置 LLM_API_KEY
- [ ] 运行 `python check_env.py` 验证环境

---

## 📍 启动成功标志

**后端日志：**
```
Application startup complete
```

**前端日志：**
```
  VITE v5.0.0  ready in 123 ms

  ➜  Local:   http://localhost:5173/
```

---

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:5173 | React Web 应用 |
| 后端 API | http://localhost:8000 | FastAPI 服务 |
| 文档 | http://localhost:8000/docs | 完整 API 文档 |

---

## 🧪 测试应用

在前端输入框中尝试：

```
今天下午是空的，想和老婆孩子出去玩几个小时，别离家太远，帮我安排一下
```

然后点击 "开始规划 ✨" 按钮。

---

## 🆘 遇到问题？

| 问题 | 解决方案 |
|------|--------|
| 后端无法启动 | 运行 `python check_env.py` 检查依赖 |
| 前端加载不了 | 清除浏览器缓存或重启 npm 服务 |
| API 超时 | 检查网络连接和 LLM_API_KEY 配置 |
| npm install 失败 | 使用镜像源: `npm config set registry https://registry.npmmirror.com` |

详见 [STARTUP_GUIDE.md](STARTUP_GUIDE.md)

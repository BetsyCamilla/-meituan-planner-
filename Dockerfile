# 使用官方 Python 镜像作为基础
FROM python:3.11-slim

# 安装 Node.js 和 npm
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装后端依赖
RUN pip install --no-cache-dir -r backend/requirements.txt

# 安装前端依赖并构建
RUN cd web && npm install && npm run build && cd ..

# 暴露端口
EXPOSE 8000 5173

# 启动脚本
RUN chmod +x start_all.py

# 启动应用
CMD ["python", "start_all.py"]

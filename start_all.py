#!/usr/bin/env python3
"""
同时启动前后端的脚本
运行: python start_all.py
"""

import os
import sys
import subprocess
from pathlib import Path
import time
import threading

def start_backend():
    """启动后端服务器"""
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    print("[后端] 启动 FastAPI 服务器...")
    os.chdir(backend_dir)
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "server:app", 
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])

def start_frontend():
    """启动前端服务器"""
    project_root = Path(__file__).parent
    web_dir = project_root / "web"
    
    # 检查依赖
    node_modules = web_dir / "node_modules"
    if not node_modules.exists():
        print("[前端] 正在安装 npm 依赖...")
        os.chdir(web_dir)
        # Windows 和其他系统的兼容性处理
        if sys.platform == "win32":
            subprocess.check_call(["npm.cmd", "install"])
        else:
            subprocess.check_call(["npm", "install"])
    
    print("[前端] 启动 Vite 开发服务器...")
    os.chdir(web_dir)
    # Windows 和其他系统的兼容性处理
    if sys.platform == "win32":
        subprocess.run(["npm.cmd", "run", "dev"])
    else:
        subprocess.run(["npm", "run", "dev"])

def main():
    print("=" * 70)
    print("🚀 启动 走起 GoNow 完整应用（前后端）")
    print("=" * 70)
    
    print("\n📦 检查依赖...")
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    requirements_file = backend_dir / "requirements.txt"
    
    if requirements_file.exists():
        try:
            import fastapi
            import uvicorn
            import sse_starlette
            print("✓ 后端依赖已安装")
        except ImportError:
            print("⚠️  后端依赖不完整，正在安装...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", str(requirements_file)
            ])
    
    print("\n🎯 启动服务...\n")
    print("=" * 70)
    print("📍 后端地址: http://localhost:8000")
    print("📍 前端地址: http://localhost:5173")
    print("📚 API 文档: http://localhost:8000/docs")
    print("=" * 70)
    print("\n💡 在浏览器打开 http://localhost:5173 开始使用")
    print("按 Ctrl+C 停止所有服务...\n")
    
    # 使用线程同时启动前后端
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    
    backend_thread.start()
    time.sleep(2)  # 给后端时间启动
    frontend_thread.start()
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 正在关闭所有服务...")
        sys.exit(0)

if __name__ == "__main__":
    main()

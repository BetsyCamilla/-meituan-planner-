#!/usr/bin/env python3
"""
启动后端服务器的脚本
运行: python start_server.py
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # 获取项目根目录
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    # 检查依赖是否已安装
    print("=" * 60)
    print("🚀 启动 走起 GoNow 后端服务器")
    print("=" * 60)
    
    print("\n📦 检查依赖...")
    requirements_file = backend_dir / "requirements.txt"
    if requirements_file.exists():
        try:
            import fastapi
            import uvicorn
            import sse_starlette
            print("✓ 所有依赖已安装")
        except ImportError:
            print("⚠️  依赖不完整，正在安装...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "-r", str(requirements_file)
            ])
    
    # 启动服务器
    print("\n🔧 启动 FastAPI 服务器...")
    print("📍 后端地址: http://localhost:8000")
    print("📚 API 文档: http://localhost:8000/docs")
    print("\n按 Ctrl+C 停止服务器...\n")
    
    os.chdir(backend_dir)
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "server:app", 
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])

if __name__ == "__main__":
    main()

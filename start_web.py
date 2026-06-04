#!/usr/bin/env python3
"""
启动前端开发服务器的脚本
运行: python start_web.py
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # 获取项目根目录
    project_root = Path(__file__).parent
    web_dir = project_root / "web"
    
    print("=" * 60)
    print("🎨 启动 走起 GoNow 前端开发服务器")
    print("=" * 60)
    
    # 检查 node_modules 是否存在
    node_modules = web_dir / "node_modules"
    if not node_modules.exists():
        print("\n📦 检查 npm 依赖...")
        print("⚠️  node_modules 不存在，正在安装...")
        os.chdir(web_dir)
        # Windows 和其他系统的兼容性处理
        if sys.platform == "win32":
            subprocess.check_call(["npm.cmd", "install"])
        else:
            subprocess.check_call(["npm", "install"])
    
    # 启动开发服务器
    print("\n🔧 启动 Vite 开发服务器...")
    print("📍 前端地址: http://localhost:5173")
    print("🔗 后端代理: http://localhost:8000")
    print("\n按 Ctrl+C 停止服务器...\n")
    
    os.chdir(web_dir)
    # Windows 和其他系统的兼容性处理
    if sys.platform == "win32":
        subprocess.run(["npm.cmd", "run", "dev"])
    else:
        subprocess.run(["npm", "run", "dev"])

if __name__ == "__main__":
    main()

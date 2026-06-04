#!/usr/bin/env python3
"""
环境检查脚本 - 验证前后端依赖是否完整
运行: python check_env.py
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python():
    """检查 Python 版本"""
    version = sys.version_info
    print(f"✓ Python 版本: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("⚠️  建议使用 Python 3.9 或更高版本")
        return False
    return True

def check_backend_deps():
    """检查后端依赖"""
    print("\n📦 检查后端依赖...")
    
    required = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'pydantic': 'Pydantic',
        'sse_starlette': 'SSE Starlette',
        'aiohttp': 'aiohttp',
        'dotenv': 'python-dotenv',
        'requests': 'requests',
    }
    
    all_ok = True
    for module, name in required.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} (未安装)")
            all_ok = False
    
    if not all_ok:
        print("\n  需要安装缺失的依赖：")
        print("  cd backend && pip install -r requirements.txt")
    
    return all_ok

def check_frontend_env():
    """检查前端环境"""
    print("\n📦 检查前端环境...")
    
    # 检查 Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        node_version = result.stdout.strip()
        print(f"  ✓ Node.js: {node_version}")
    except FileNotFoundError:
        print("  ✗ Node.js 未安装")
        print("  请从 https://nodejs.org/ 下载安装")
        return False
    
    # 检查 npm
    try:
        # Windows 上使用 npm.cmd，其他系统使用 npm
        npm_cmd = 'npm.cmd' if sys.platform == 'win32' else 'npm'
        result = subprocess.run([npm_cmd, '--version'], capture_output=True, text=True)
        npm_version = result.stdout.strip()
        print(f"  ✓ npm: {npm_version}")
    except FileNotFoundError:
        print("  ✗ npm 未安装")
        return False
    
    # 检查 node_modules
    web_dir = Path(__file__).parent / "web"
    node_modules = web_dir / "node_modules"
    if node_modules.exists():
        print(f"  ✓ node_modules 已安装")
    else:
        print(f"  ⚠️  node_modules 不存在")
        print("  需要运行: cd web && npm install")
        return False
    
    return True

def check_config():
    """检查配置文件"""
    print("\n⚙️  检查配置文件...")
    
    backend_dir = Path(__file__).parent / "backend"
    env_file = backend_dir / ".env"
    
    if env_file.exists():
        with open(env_file) as f:
            content = f.read()
            if "LLM_API_KEY=" in content and len(content.split("=")[1].strip()) > 0:
                print("  ✓ .env 文件存在且已配置")
            else:
                print("  ⚠️  .env 文件存在但 LLM_API_KEY 未配置")
                print("  请编辑 backend/.env 配置 LLM API")
                return False
    else:
        print("  ✗ .env 文件不存在")
        return False
    
    return True

def main():
    print("=" * 60)
    print("🔍 走起 GoNow 环境检查")
    print("=" * 60)
    
    checks = [
        ("Python 版本", check_python),
        ("后端依赖", check_backend_deps),
        ("前端环境", check_frontend_env),
        ("配置文件", check_config),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ 检查出错: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 检查结果")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✨ 所有检查通过！")
        print("可以运行: python start_all.py")
    else:
        print("⚠️  请先解决上述问题再启动服务")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

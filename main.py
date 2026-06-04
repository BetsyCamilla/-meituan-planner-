#!/usr/bin/env python3
"""
美团短时活动规划 Agent — CLI 演示入口

用法:
    python main.py "今天下午是空的，想和老婆孩子出去玩几个小时，别离家太远，帮我安排一下"
    python main.py "今天下午是空的，想和朋友出去聚会，4个人，2男2女，帮我安排一下"
"""

import asyncio
import json
import sys
from pathlib import Path

# 将项目根目录加入路径
sys.path.insert(0, str(Path(__file__).parent))

from agent.intent_parser import parse_intent
from agent.explorer import Explorer
from agent.planner import Planner, format_plan_md
from agent.executor import Executor


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


async def run_planner(message: str, auto_execute: bool = False):
    """
    核心流程：解析 → 探索 → 规划 → 执行
    """
    print_section("🔍 第1步：意图解析")
    intent = parse_intent(message)
    print(f"  场景：{intent.scene}")
    print(f"  日期：{intent.date}")
    print(f"  时长：{intent.duration_hours} 小时")
    if intent.has_child:
        print(f"  孩子：{intent.child_age} 岁")
    if intent.wife_dieting:
        print(f"  老婆：在减肥 🥗")
    if intent.scene == "friends":
        print(f"  朋友：共 {intent.group_size} 人（{intent.group_male}男 {intent.group_female}女）")
    if intent.needs_delivery:
        print(f"  配送需求：{intent.delivery_item}")

    print_section("🗺️ 第2步：探索候选（玩/吃/活动）")
    explorer = Explorer(intent)
    candidates = await explorer.explore()
    print(f"  找到 {len(candidates['venues'])} 个活动/景点")
    print(f"  找到 {len(candidates['restaurants'])} 家餐厅")
    print(f"  找到 {len(candidates['activities'])} 个朋友聚会活动")

    for key, items in candidates.items():
        if items:
            print(f"\n  [{key}] TOP 3:")
            for item in items[:3]:
                print(f"    • {item.name}（{item.category}）评分:{item.rating} "
                      f"{'免费' if item.price == 0 else f'{item.price}元'}")

    print_section("📋 第3步：生成行程计划")
    planner = Planner(intent)
    plan = planner.make_plan(
        venues=candidates["venues"],
        restaurants=candidates["restaurants"],
        activities=candidates["activities"],
    )
    plan_md = format_plan_md(plan)
    print(plan_md)

    # 异常检测
    if plan.warnings:
        print("⚠️  警告信息：")
        for w in plan.warnings:
            print(f"  - {w}")

    # 自动执行
    if auto_execute:
        print_section("📦 第4步：自动下单/预约")
        executor = Executor(intent)
        report = executor.execute(plan)
        print(report.summary())
    else:
        print_section("📦 等待确认后下单/预约")
        print("  输入 confirm 开始自动下单，或按 Ctrl+C 退出")

    return plan


async def interactive_confirm(message: str):
    """带确认的交互模式"""
    plan = await run_planner(message, auto_execute=False)
    try:
        cmd = input("\n> 确认方案并下单 (confirm/q): ").strip().lower()
        if cmd == "confirm":
            from agent.intent_parser import UserIntent
            executor = Executor(UserIntent())
            report = executor.execute(plan)
            print_section("📦 执行报告")
            print(report.summary())
        else:
            print("已退出，未执行下单。")
    except (EOFError, KeyboardInterrupt):
        print("\n已退出。")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n示例：")
        print('  python main.py "今天下午是空的，想和老婆孩子出去玩几个小时，别离家太远"')
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    print(f"\n📨 用户输入：{message}\n")

    # 检查是否带 --auto 参数
    auto = "--auto" in sys.argv
    if auto:
        asyncio.run(run_planner(message, auto_execute=True))
    else:
        asyncio.run(interactive_confirm(message))


if __name__ == "__main__":
    main()
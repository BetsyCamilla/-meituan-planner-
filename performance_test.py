"""
性能测试脚本 - 评估 走起 GoNow 的响应时间、吞吐量和稳定性

用法：
    python performance_test.py
    python performance_test.py --duration 60 --concurrent 10
"""

import asyncio
import time
import json
import statistics
import argparse
from typing import List, Dict
import aiohttp
from datetime import datetime

# 配置
API_BASE = "http://localhost:8000"
PLAN_ENDPOINT = f"{API_BASE}/api/plan/stream"
HEALTH_ENDPOINT = f"{API_BASE}/api/health"

# 测试场景
TEST_SCENARIOS = [
    {
        "name": "亲子活动",
        "message": "今天下午是空的，想和老婆孩子出去玩几个小时，别离家太远，帮我安排一下",
        "user_lat": 31.2304,
        "user_lng": 121.4737,
    },
    {
        "name": "朋友聚会",
        "message": "周末下午想和朋友聚会，4个人，2男2女，有哪些好玩的？",
        "user_lat": 31.2304,
        "user_lng": 121.4737,
    },
    {
        "name": "情侣约会",
        "message": "想和女朋友在南京西路附近找个地方下午小约会，看电影或者吃饭都行",
        "user_lat": 31.2304,
        "user_lng": 121.4737,
    },
]

class PerformanceTest:
    def __init__(self):
        self.results: List[Dict] = []
        self.errors = 0
        self.successes = 0
        
    async def health_check(self) -> bool:
        """检查后端服务健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(HEALTH_ENDPOINT, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✓ 后端服务健康：{data}")
                        return True
                    else:
                        print(f"✗ 后端服务异常：{resp.status}")
                        return False
        except Exception as e:
            print(f"✗ 无法连接后端：{e}")
            return False

    async def test_single_request(self, scenario: Dict) -> Dict:
        """测试单个请求"""
        start_time = time.time()
        events_received = 0
        first_event_time = None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    PLAN_ENDPOINT,
                    json={
                        "message": scenario["message"],
                        "user_lat": scenario["user_lat"],
                        "user_lng": scenario["user_lng"],
                    },
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status != 200:
                        return {
                            "scenario": scenario["name"],
                            "success": False,
                            "error": f"HTTP {resp.status}",
                            "duration": time.time() - start_time,
                        }
                    
                    async for line in resp.content:
                        if first_event_time is None:
                            first_event_time = time.time() - start_time
                        events_received += 1
                        
                        # 每收到10个事件打印一次进度
                        if events_received % 10 == 0:
                            print(f"  → 已接收 {events_received} 个事件...")
            
            duration = time.time() - start_time
            return {
                "scenario": scenario["name"],
                "success": True,
                "duration": duration,
                "first_event_time": first_event_time,
                "events_received": events_received,
                "events_per_second": events_received / duration if duration > 0 else 0,
            }
        except asyncio.TimeoutError:
            return {
                "scenario": scenario["name"],
                "success": False,
                "error": "超时（120秒）",
                "duration": time.time() - start_time,
            }
        except Exception as e:
            return {
                "scenario": scenario["name"],
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
            }

    async def concurrent_requests(self, concurrent: int, duration: int) -> None:
        """并发测试"""
        print(f"\n📊 并发测试：{concurrent} 并发，{duration} 秒")
        print("=" * 60)
        
        start_time = time.time()
        tasks = []
        scenario_idx = 0
        
        while time.time() - start_time < duration:
            # 创建新任务直到达到并发数
            while len(tasks) < concurrent and time.time() - start_time < duration:
                scenario = TEST_SCENARIOS[scenario_idx % len(TEST_SCENARIOS)]
                task = asyncio.create_task(self.test_single_request(scenario))
                tasks.append(task)
                scenario_idx += 1
            
            # 等待至少一个任务完成
            if tasks:
                done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for result in done:
                    result_data = await result
                    self.results.append(result_data)
                    
                    if result_data["success"]:
                        self.successes += 1
                        print(f"✓ {result_data['scenario']}: {result_data['duration']:.2f}s")
                    else:
                        self.errors += 1
                        print(f"✗ {result_data['scenario']}: {result_data['error']}")
        
        # 等待剩余任务完成
        if tasks:
            done, _ = await asyncio.wait(tasks)
            for result in done:
                result_data = await result
                self.results.append(result_data)
                if result_data["success"]:
                    self.successes += 1
                else:
                    self.errors += 1

    async def run_sequential_test(self) -> None:
        """顺序测试所有场景"""
        print("\n🧪 顺序测试")
        print("=" * 60)
        
        for scenario in TEST_SCENARIOS:
            print(f"\n测试场景：{scenario['name']}")
            print(f"消息：{scenario['message'][:50]}...")
            
            result = await self.test_single_request(scenario)
            self.results.append(result)
            
            if result["success"]:
                self.successes += 1
                print(f"✓ 耗时：{result['duration']:.2f}s")
                print(f"  首个事件时间：{result['first_event_time']:.2f}s")
                print(f"  事件数量：{result['events_received']}")
                print(f"  吞吐量：{result['events_per_second']:.1f} 事件/秒")
            else:
                self.errors += 1
                print(f"✗ 错误：{result['error']}")

    def generate_report(self) -> None:
        """生成性能报告"""
        if not self.results:
            print("❌ 没有测试结果")
            return
        
        successful_results = [r for r in self.results if r.get("success", False)]
        
        if not successful_results:
            print("❌ 所有测试都失败了")
            return
        
        durations = [r["duration"] for r in successful_results]
        first_events = [r.get("first_event_time", 0) for r in successful_results if "first_event_time" in r]
        events_counts = [r.get("events_received", 0) for r in successful_results if "events_received" in r]
        
        print("\n" + "=" * 60)
        print("📈 性能报告")
        print("=" * 60)
        
        print("\n【总体统计】")
        print(f"总请求数：{len(self.results)}")
        print(f"成功：{self.successes} ✓")
        print(f"失败：{self.errors} ✗")
        print(f"成功率：{self.successes / len(self.results) * 100:.1f}%")
        
        if durations:
            print("\n【响应时间】（单位：秒）")
            print(f"平均：{statistics.mean(durations):.2f}s")
            print(f"最小：{min(durations):.2f}s")
            print(f"最大：{max(durations):.2f}s")
            if len(durations) > 1:
                print(f"中位数：{statistics.median(durations):.2f}s")
                print(f"标准差：{statistics.stdev(durations):.2f}s")
        
        if first_events:
            print("\n【首个事件时间】（单位：秒）")
            print(f"平均：{statistics.mean(first_events):.3f}s")
            print(f"最小：{min(first_events):.3f}s")
            print(f"最大：{max(first_events):.3f}s")
        
        if events_counts:
            print("\n【事件流量】")
            print(f"平均事件数：{statistics.mean(events_counts):.0f}")
            print(f"最小事件数：{min(events_counts)}")
            print(f"最大事件数：{max(events_counts)}")
        
        print("\n【场景性能分布】")
        for scenario in TEST_SCENARIOS:
            scenario_results = [r for r in successful_results if r["scenario"] == scenario["name"]]
            if scenario_results:
                scenario_times = [r["duration"] for r in scenario_results]
                print(f"\n{scenario['name']}：")
                print(f"  请求数：{len(scenario_results)}")
                print(f"  平均时间：{statistics.mean(scenario_times):.2f}s")
                print(f"  最快：{min(scenario_times):.2f}s，最慢：{max(scenario_times):.2f}s")
        
        # 保存详细报告到文件
        report_path = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": len(self.results),
                    "successful": self.successes,
                    "failed": self.errors,
                    "success_rate": self.successes / len(self.results),
                },
                "results": self.results,
            }, f, indent=2, ensure_ascii=False)
        print(f"\n📄 详细报告已保存到：{report_path}")


async def main():
    parser = argparse.ArgumentParser(description="走起 GoNow 性能测试")
    parser.add_argument(
        "--mode",
        choices=["sequential", "concurrent"],
        default="sequential",
        help="测试模式（默认：sequential）",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=5,
        help="并发数（仅在 concurrent 模式生效，默认：5）",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="测试持续时间（秒，仅在 concurrent 模式生效，默认：60）",
    )
    
    args = parser.parse_args()
    
    tester = PerformanceTest()
    
    # 健康检查
    print("🏥 健康检查...")
    if not await tester.health_check():
        print("❌ 后端服务未运行，请先启动后端")
        return
    
    # 运行测试
    if args.mode == "sequential":
        await tester.run_sequential_test()
    else:
        await tester.concurrent_requests(args.concurrent, args.duration)
    
    # 生成报告
    tester.generate_report()


if __name__ == "__main__":
    asyncio.run(main())

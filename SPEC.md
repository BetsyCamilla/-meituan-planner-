# 美团短时活动规划 Agent — 设计文档

## 1. 需求分析

### 1.1 场景描述

用户给美团发一条自然语言消息，系统在几分钟内输出可执行的完整方案，并自动完成关键下单/预订动作。

**输入示例：**
> "今天下午是空的，想和老婆孩子/朋友出去玩几个小时，别离家太远，帮我安排一下"

**输出：** 包含玩什么、去哪吃、有没有额外活动的一体化方案，小明确认后可一键下单/预约。

### 1.2 核心场景

| 场景 | 群体特征 | 约束 |
|------|---------|------|
| 家庭 | 孩子5岁，老婆在减肥 | 亲子友好、近距离、适合儿童活动 |
| 朋友 | 4人（2男2女） | 均衡选择、聚会属性 |

### 1.3 用户痛点

- 信息分散（玩/吃/活动需要在不同页面搜索）
- 不知道有没有位置、要不要排队
- 安排好后还要手动一个个下单

---

## 2. Planning 策略

### 2.1 三层规划模型

```
用户输入
  │
  ▼
【意图层】IntentParser — 判断场景类型、提取关键参数
  │ family / friends
  ▼
【探索层】ExplorerAgent — 并行调用多个工具搜索候选
  │ ┌──────────────────────────────────┐
  │ ▼          ▼          ▼             │
  │ 亲子活动  餐厅    朋友聚会活动       │
  │ nearby   restaurant  nearby        │
  │ search   search      search        │
  │ └──────────────────────────────────┘
  ▼
【规划层】PlannerAgent — 排序+组合+时间窗口校验
  │ 生成带时间轴的可执行方案
  │ 输出 order_payload
  ▼
【执行层】Executor — 批量下单/预约（Mock）
```

### 2.2 时间窗口规划

下午 4–6 小时活动窗口：
- 14:00 出发 → 14:30–17:00 玩 → 17:30–19:00 晚餐 → 可选蛋糕/鲜花配送

---

## 3. 工具调用链路

### 3.1 核心工具（Mock 实现）

| 工具 | 能力 | Mock 数据源 |
|------|------|-----------|
| `location_nearby_search` | 按关键词+半径查附近地点 | `mock_poi.json` |
| `restaurant_search` | 搜餐厅，支持菜系/人均/排队筛选 | `mock_restaurant.json` |
| `venue_detail` | 获取景点/乐园详情和票种 | `mock_venue.json` |
| `table_booking` | 餐厅订座 | 随机成功/需排队 |
| `ticket_create` | 创建订单（景点门票/活动票） | 固定成功 |
| `delivery_order` | 配送订单（蛋糕/鲜花） | 固定成功 |

### 3.2 调用链路图

```
IntentParser
  │
  ├─► EXPLORE (并行)
  │     ├─ search_kid_friendly_venues  ──► venue_filter_by_age(kid=5)
  │     ├─ search_restaurants          ──► filter_by_diet(wife=减肥)
  │     └─ search_friend_activities    ──► group_activity_filter(group=4)
  │
  └─► PLAN
        ├─ time_window_allocator        ──► 14:00-20:00 时间轴
        ├─ venue_ranker                 ──► 距离+评分+类型综合排序
        └─ order_payload_builder        ──► 合并下单指令
              │
              ▼
         Executor (批量执行)
              ├─ ticket_create (亲子乐园票)
              ├─ table_booking (餐厅订座)
              └─ delivery_order (蛋糕/鲜花，可选)
```

---

## 4. 异常处理机制

| 异常场景 | 处理策略 |
|---------|---------|
| 附近无合适亲子乐园 | 扩大半径至5km，或推荐户外公园 |
| 餐厅满座/需排队 | 自动尝试下一家备选，或推荐错峰 |
| 活动总时长超出 | 自动压缩/删除低优先级项目 |
| 工具调用超时 | 重试1次，失败后返回部分方案+警告 |
| 用户否定方案 | 进入对话修正模式，收集反馈重新规划 |
| 配送商品缺货 | 询问是否替换或跳过 |

---

## 5. 交付物清单

```
meituan-planner/
├── SPEC.md                      # 本文档
├── main.py                      # CLI 入口（演示用）
├── agent/
│   ├── __init__.py
│   ├── intent_parser.py         # 意图解析
│   ├── explorer.py              # 探索/搜索
│   ├── planner.py               # 规划排序
│   └── executor.py              # 执行下单
├── tools/
│   ├── __init__.py
│   ├── meituan_api.py           # Mock 美团 API
│   └── mock_data.py             # Mock 数据
├── output/
│   └── 方案.md                   # 输出样例
└── tests/
    └── test_planner.py          # 基础测试
```
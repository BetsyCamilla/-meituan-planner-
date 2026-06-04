# 第三方致谢与说明

LeisureAgent 的两项核心设计**受以下项目启发**，但本仓库中的相关代码均为**独立实现**，
**并非这两个项目源码的再分发**：

- **DinoZone** —— 启发了「时间线骨架模板」（伙伴 × 天气 × 时段）、多级降级策略、概率预订模拟的设计思路。
  本项目对应实现见 `agent/enhanced_planner.py`（骨架为内置硬编码，不读取 DinoZone 的任何文件）。
- **LeisureAgent（同名参考项目）** —— 启发了 ReAct 搜索/执行自愈、LLM 输出 POI 校验（防止模型虚构地点）的设计思路。
  本项目对应实现见 `agent/enhanced_planner.py` 中的 `ReActSearchHealer` / `ReActExecuteHealer` / `validate_llm_plan`。

> 上述两个项目的源码**不包含在本仓库中**。本项目仅借鉴其设计理念，所有代码由本项目作者独立编写，
> 以 MIT 许可证开源。如果你是这两个项目的作者并对本致谢有任何意见，欢迎通过 issue 联系。

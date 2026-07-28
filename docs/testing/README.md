# Testing

本目录用于后续维护测试策略、测试分层、测试数据规则和质量门槛。

公共后端底座已建立 pytest、pytest-asyncio、httpx 和 Ruff 配置，详细说明见 `backend-foundation.md`。测试使用隔离 SQLite 与合成数据，不访问真实平台、模型或生产数据库。

成员二模拟业务数据的迁移、全量导入、幂等和拒绝非模拟数据测试见 `commerce-data-foundation.md`。

成员三分析、评论、改良、内容、Prompt、模型调用和报告持久化测试见 `analysis-persistence.md`。

智能选品利润、评分、缺失数据和稳定排序单元测试见 `selection-scoring.md`。

智能选品 Service、持久化、结构化 Tool、解释校验与导出测试见 `selection-api-tools.md`。

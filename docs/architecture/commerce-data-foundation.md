# 成员二数据与持久化基础

## 范围

本阶段实现成员二模拟业务数据的持久化与初始化能力，不实现业务 API、完整 `MockShopeeAdapter`、页面或真实 Shopee 接入。

## 数据流

```text
data/demo/shopee_mock/*.csv
  → Pydantic CSV Row Schema
  → CommerceImportService
  → CommerceImportRepository
  → SQLAlchemy commerce models
→ PostgreSQL / isolated `sellpilot_test`
```

路由和上层 Agent 不读取 CSV。后续业务能力通过 Repository、Service 和 `PlatformAdapter` 使用统一实体。

## 表

迁移 `20260728_0003` 创建：

- `shops`
- `products`
- `skus`
- `inventory_records`
- `orders`
- `order_items`
- `reviews`
- `logistics_records`
- `logistics_tracks`
- `customer_sessions`
- `customer_messages`
- `returns_refunds`
- `category_trends`

应用表使用 UUID 主键，稳定源标识使用唯一的 `external_id`。所有导入表保留 `source_type` 和 `is_mock_data`。

## 单店铺边界

数据包按六个站点提供 `SHOP001` 至 `SHOP006`。系统不把它们解释为六个应用店铺：

- 数据库只创建一个 `SELLPILOT_MOCK_SHOP`。
- 商品和订单通过 UUID 外键关联该逻辑店铺。
- 原始站点店铺标识保存在 `source_shop_external_id`。

因此数据可追踪，同时保持首版单模拟店铺边界。

## 导入事务

- 12 个文件必须同时存在。
- 所有行先通过明确的 Pydantic Schema。
- 只允许 `is_mock_data=true`。
- 金额、数量、日期和订单金额关系在写入前校验。
- Service 不提交事务；CLI 或调用方统一提交或回滚。
- 重复导入通过各表 `external_id` 跳过现有记录。

当前策略只插入缺失记录，不覆盖数据库中的人工修改。后续如需更新模式，必须增加显式策略、批次记录和操作审计。

## 删除与安全

核心业务外键使用 `RESTRICT`。物流轨迹和客服消息只对父记录使用 `CASCADE`，不开放公共任意删除 API。导入包为合成数据，不包含真实买家资料、账号或平台密钥。

## 未实现

- 商品、库存、订单和物流业务 API。
- 价格、库存、上下架等确认后写操作。
- `MockShopeeAdapter` 的业务查询和故障模拟。
- 数据导入页面、进度任务和批次历史。
- PostgreSQL 受控环境兼容性验收。

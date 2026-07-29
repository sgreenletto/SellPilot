# 成员二数据契约与数据库设计

## 1. 文档状态

- 所属阶段：成员二数据与模拟平台基础设计。
- 当前状态：设计基线，尚未创建业务表、迁移、导入服务或业务 API。
- 数据来源：`data/demo/shopee_mock/` 中的 12 个 CSV、生成器、校验器和说明文档。
- 数据性质：全部为合成实验数据，不代表真实 Shopee 店铺或生产接口数据。
- 运行与测试数据库统一使用 PostgreSQL；测试必须使用独立数据库。

本设计遵循首版单用户、单模拟店铺和 `MockShopeeAdapter` 边界。后续正式表结构必须通过 Alembic 迁移创建，不得在应用启动时调用 `create_all`。

## 2. 设计决策

### 2.1 标识策略

- 业务表使用应用内部 UUID `id` 作为主键，与现有公共模型保持一致。
- CSV 和未来平台返回的标识保存为 `external_id`，在各实体范围内建立唯一约束。
- 导入服务先通过 `external_id` 查找内部 UUID，再写入外键。
- API 和平台适配器可以把 `external_id` 作为面向模拟平台的业务标识，但 Repository 关系只使用 UUID。
- 不把 CSV 行号、文件路径或标题作为主键。

### 2.2 公共追踪字段

所有导入业务表至少包含：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `id` | UUID | 内部主键 |
| `external_id` | String(100) | CSV/平台标识，实体内唯一 |
| `source_type` | String(50) | 当前固定为 `simulated_experiment` |
| `is_mock_data` | Boolean | 当前必须为 `true` |
| `source_updated_at` | DateTime(timezone=True), nullable | 源数据更新时间 |
| `created_at` | DateTime(timezone=True) | 应用记录创建时间 |
| `updated_at` | DateTime(timezone=True) | 应用记录更新时间 |

导入任务本身还应记录文件名、文件校验值、导入批次、开始/结束时间、成功/失败行数和错误摘要。该记录在后续“模拟数据导入”任务中设计，不与业务表混合。

### 2.3 金额、时间和文本

- 金额使用 `Numeric(18, 4)`，不得使用浮点数。
- 计数和库存使用非负整数约束。
- 时间统一解析为带时区时间并以 UTC 保存；API 按站点或用户时区展示。
- 趋势日期使用 `Date`。
- 多语言文本使用 Unicode `Text`。
- 货币保留原币种，不在导入阶段执行汇率换算。
- `buyer_id` 仅保存数据包中的合成脱敏标识，不建立买家个人资料表。

## 3. 实体关系

```text
shops
  ├─ products
  └─ orders

products
  ├─ skus
  ├─ order_items
  ├─ reviews
  └─ customer_sessions

skus
  ├─ inventory_records
  ├─ order_items
  └─ reviews

orders
  ├─ order_items
  ├─ reviews
  ├─ logistics_records
  ├─ customer_sessions
  └─ returns_refunds

logistics_records
  └─ logistics_tracks

customer_sessions
  └─ customer_messages

order_items
  └─ returns_refunds
```

`category_trends` 按站点、类目和日期独立存储，不直接外键到商品表，避免把市场趋势类目误绑定为店铺商品类目。

## 4. CSV 与业务表映射

### 4.1 `shops`（由数据集去重生成）

数据包没有独立 `shops.csv`，且六个站点分别使用 `SHOP001` 至 `SHOP006`。首版仍坚持单模拟店铺：导入服务创建一个内部逻辑店铺 `SELLPILOT_MOCK_SHOP`，各行原始站点店铺标识保存在商品和订单的 `source_shop_external_id` 中。

| 目标字段 | 来源 | 类型与约束 |
| --- | --- | --- |
| `external_id` | 固定值 | String(100)，`SELLPILOT_MOCK_SHOP`，唯一 |
| `name` | 固定值 | String(200)，`SellPilot Mock Shop` |
| `platform` | `products.platform` | String(50)，当前为 Shopee 模拟值 |
| `mode` | 固定值 | String(32)，`mock` |
| `is_active` | 固定值 | Boolean，`true` |

首版导入结果必须只有一个内部店铺；站点级 `shop_id` 不创建额外店铺记录，也不得丢弃。

### 4.2 `products.csv` → `products`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `product_id` | `external_id` | String(100)，唯一 |
| `shop_id` | 固定映射 | UUID FK → 单个 `shops.id` |
| `shop_id` | `source_shop_external_id` | String(100)，保留站点级源标识 |
| `title` | `title` | String(500)，非空 |
| `category_id` | `category_external_id` | String(100)，非空 |
| `category_name` | `category_name` | String(200)，非空 |
| `description` | `description` | Text |
| `platform` | `platform` | String(50) |
| `site` | `site` | String(32)，受控枚举 |
| `source_type` | `source_type` | String(50) |
| `currency` | `currency` | String(3)，受控枚举 |
| `price` | `price` | Numeric(18,4)，`>= 0` |
| `cost` | `cost` | Numeric(18,4)，`>= 0` |
| `shipping_cost` | `shipping_cost` | Numeric(18,4)，`>= 0` |
| `sales_count` | `sales_count` | Integer，`>= 0` |
| `rating` | `rating` | Numeric(3,2)，`0..5` |
| `review_count` | `review_count` | Integer，`>= 0` |
| `favorite_count` | `favorite_count` | Integer，`>= 0` |
| `status` | `status` | `draft/active/inactive/archived` |
| `created_at` | `source_created_at` | DateTime(timezone=True) |
| `updated_at` | `source_updated_at` | DateTime(timezone=True) |
| `collected_at` | `collected_at` | DateTime(timezone=True) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

`shop_name` 仅用于生成和校验 `shops`，不在商品行重复保存。

### 4.3 `skus.csv` → `skus`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `sku_id` | `external_id` | String(100)，唯一 |
| `product_id` | `product_id` | UUID FK → `products.id` |
| `seller_sku` | `seller_sku` | String(100)，唯一 |
| `variation_name` | `variation_name` | String(100) |
| `variation_value` | `variation_value` | String(200) |
| `price` | `price` | Numeric(18,4)，`>= 0` |
| `cost` | `cost` | Numeric(18,4)，`>= 0` |
| `weight` | `weight` | Numeric(12,4)，`>= 0` |
| `status` | `status` | `active/inactive` |
| `created_at` | `source_created_at` | DateTime(timezone=True) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

### 4.4 `inventory.csv` → `inventory_records`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `inventory_id` | `external_id` | String(100)，唯一 |
| `sku_id` | `sku_id` | UUID FK → `skus.id` |
| `warehouse_id` | `warehouse_external_id` | String(100) |
| `warehouse_name` | `warehouse_name` | String(200) |
| `available_stock` | `available_stock` | Integer，`>= 0` |
| `reserved_stock` | `reserved_stock` | Integer，`>= 0` |
| `safety_stock` | `safety_stock` | Integer，`>= 0` |
| `stock_status` | `stock_status` | `sufficient/low_stock/out_of_stock` |
| `updated_at` | `source_updated_at` | DateTime(timezone=True) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

首版允许一个 SKU 在一个仓库一条当前库存记录，唯一约束为 `(sku_id, warehouse_external_id)`。库存流水在商品与库存写操作任务中单独增加，不复用当前快照表。

### 4.5 `orders.csv` → `orders`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `order_id` | `external_id` | String(100)，唯一 |
| `shop_id` | 固定映射 | UUID FK → 单个 `shops.id` |
| `shop_id` | `source_shop_external_id` | String(100)，保留站点级源标识 |
| `buyer_id` | `buyer_external_id` | String(100)，合成脱敏标识 |
| `site` | `site` | String(32)，受控枚举 |
| `currency` | `currency` | String(3)，受控枚举 |
| `order_status` | `order_status` | 受控枚举 |
| `payment_status` | `payment_status` | `unpaid/paid/refunded` |
| `subtotal` | `subtotal` | Numeric(18,4)，`>= 0` |
| `shipping_fee` | `shipping_fee` | Numeric(18,4)，`>= 0` |
| `discount_amount` | `discount_amount` | Numeric(18,4)，`>= 0` |
| `total_amount` | `total_amount` | Numeric(18,4)，`>= 0` |
| `created_at` | `source_created_at` | DateTime(timezone=True) |
| `paid_at` | `paid_at` | DateTime(timezone=True), nullable |
| `shipped_at` | `shipped_at` | DateTime(timezone=True), nullable |
| `completed_at` | `completed_at` | DateTime(timezone=True), nullable |
| `cancelled_at` | `cancelled_at` | DateTime(timezone=True), nullable |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

金额校验：`total_amount = subtotal + shipping_fee - discount_amount`。

### 4.6 `order_items.csv` → `order_items`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `order_item_id` | `external_id` | String(100)，唯一 |
| `order_id` | `order_id` | UUID FK → `orders.id` |
| `product_id` | `product_id` | UUID FK → `products.id` |
| `sku_id` | `sku_id` | UUID FK → `skus.id` |
| `quantity` | `quantity` | Integer，`> 0` |
| `unit_price` | `unit_price` | Numeric(18,4)，`>= 0` |
| `subtotal` | `subtotal` | Numeric(18,4)，`>= 0` |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

行金额校验：`subtotal = unit_price × quantity`；SKU 必须属于同一行指定的商品。

### 4.7 `logistics.csv` → `logistics_records`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `logistics_id` | `external_id` | String(100)，唯一 |
| `order_id` | `order_id` | UUID FK → `orders.id`，唯一 |
| `tracking_number` | `tracking_number` | String(100)，唯一 |
| `carrier` | `carrier` | String(100) |
| `logistics_status` | `status` | 受控枚举 |
| `origin` | `origin` | String(200) |
| `destination` | `destination` | String(200) |
| `estimated_delivery_at` | `estimated_delivery_at` | DateTime(timezone=True), nullable |
| `latest_location` | `latest_location` | String(200), nullable |
| `updated_at` | `source_updated_at` | DateTime(timezone=True) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

### 4.8 `logistics_tracks.csv` → `logistics_tracks`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `track_id` | `external_id` | String(100)，唯一 |
| `tracking_number` | `logistics_id` | 先解析为 UUID FK → `logistics_records.id` |
| `status` | `status` | 受控枚举 |
| `location` | `location` | String(200) |
| `description` | `description` | Text |
| `event_time` | `event_time` | DateTime(timezone=True) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

索引 `(logistics_id, event_time)`；同一物流单轨迹时间必须单调递增。

### 4.9 `returns_refunds.csv` → `returns_refunds`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `return_id` | `external_id` | String(100)，唯一 |
| `order_id` | `order_id` | UUID FK → `orders.id` |
| `order_item_id` | `order_item_id` | UUID FK → `order_items.id` |
| `buyer_id` | `buyer_external_id` | String(100)，合成脱敏标识 |
| `request_type` | `request_type` | `refund_only/return_and_refund` |
| `reason_type` | `reason_type` | 受控枚举 |
| `reason_description` | `reason_description` | Text |
| `amount` | `amount` | Numeric(18,4)，`>= 0` |
| `status` | `status` | `requested/approved/rejected/completed` |
| `requested_at` | `requested_at` | DateTime(timezone=True) |
| `completed_at` | `completed_at` | DateTime(timezone=True), nullable |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

### 4.10 `reviews.csv` → `reviews`

评论数据由成员二负责治理和提供，分析算法属于成员三。

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `review_id` | `external_id` | String(100)，唯一 |
| `product_id` | `product_id` | UUID FK → `products.id` |
| `sku_id` | `sku_id` | UUID FK → `skus.id`, nullable |
| `order_id` | `order_id` | UUID FK → `orders.id`, nullable |
| `buyer_id` | `buyer_external_id` | String(100)，合成脱敏标识 |
| `rating` | `rating` | SmallInteger，`1..5` |
| `content` | `content` | Text |
| `content_zh` | `content_zh` | Text, nullable |
| `language` | `language` | String(32)，受控枚举 |
| `sentiment_hint` | `sentiment_hint` | String(32)，实验标签，不是正式 AI 结论 |
| `issue_type` | `issue_type` | String(50)，实验标签 |
| `created_at` | `source_created_at` | DateTime(timezone=True) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

为兼容未来公开评论，`sku_id` 和 `order_id` 允许为空；当前模拟数据导入时仍须验证引用完整。

### 4.11 `customer_sessions.csv` → `customer_sessions`

成员二负责数据和查询接口；客服意图、RAG 和回复逻辑属于成员四。

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `session_id` | `external_id` | String(100)，唯一 |
| `buyer_id` | `buyer_external_id` | String(100)，合成脱敏标识 |
| `order_id` | `order_id` | UUID FK → `orders.id`, nullable |
| `product_id` | `product_id` | UUID FK → `products.id`, nullable |
| `language` | `language` | String(32)，受控枚举 |
| `intent` | `intent` | String(50)，实验标签 |
| `risk_level` | `risk_level` | String(32)，客服风险标签 |
| `session_status` | `status` | `open/resolved/transferred_to_human` |
| `created_at` | `source_created_at` | DateTime(timezone=True) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

### 4.12 `customer_messages.csv` → `customer_messages`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `message_id` | `external_id` | String(100)，唯一 |
| `session_id` | `session_id` | UUID FK → `customer_sessions.id` |
| `sender_type` | `sender_type` | `buyer/assistant` |
| `content` | `content` | Text |
| `language` | `language` | String(32)，受控枚举 |
| `message_time` | `message_time` | DateTime(timezone=True) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

索引 `(session_id, message_time)`；模拟发送属于写操作，必须先进入待确认任务。

### 4.13 `category_trends.csv` → `category_trends`

| CSV 字段 | 目标字段 | 类型与约束 |
| --- | --- | --- |
| `trend_id` | `external_id` | String(100)，唯一 |
| `site` | `site` | String(32)，受控枚举 |
| `category_id` | `category_external_id` | String(100) |
| `category_name` | `category_name` | String(200) |
| `date` | `date` | Date |
| `search_index` | `search_index` | Numeric(12,4)，`>= 0` |
| `sales_index` | `sales_index` | Numeric(12,4)，`>= 0` |
| `competition_index` | `competition_index` | Numeric(12,4)，`>= 0` |
| `average_price` | `average_price` | Numeric(18,4)，`>= 0` |
| `growth_rate` | `growth_rate` | Numeric(12,6) |
| `is_mock_data` | `is_mock_data` | Boolean，必须为 `true` |

唯一约束 `(site, category_external_id, date)`，用于趋势查询和防止重复导入。

## 5. 受控枚举基线

枚举值来自当前模拟数据。数据库列使用字符串并配合应用层 `StrEnum` 和 Schema 校验，避免 PostgreSQL 原生枚举给后续迁移带来额外成本。

- 站点：`Indonesia`、`Malaysia`、`Philippines`、`Singapore`、`Thailand`、`Vietnam`。
- 货币：`IDR`、`MYR`、`PHP`、`SGD`、`THB`、`VND`。
- 商品状态：`draft`、`active`、`inactive`、`archived`。
- SKU 状态：`active`、`inactive`。
- 库存状态：`sufficient`、`low_stock`、`out_of_stock`。
- 订单状态：`pending_payment`、`paid`、`ready_to_ship`、`shipped`、`delivered`、`completed`、`cancelled`、`refund_requested`、`refunded`。
- 支付状态：`unpaid`、`paid`、`refunded`。
- 物流状态：`pending_pickup`、`picked_up`、`in_transit`、`customs_clearance`、`out_for_delivery`、`delivered`、`exception`。
- 售后请求：`refund_only`、`return_and_refund`。
- 售后状态：`requested`、`approved`、`rejected`、`completed`。
- 会话状态：`open`、`resolved`、`transferred_to_human`。
- 消息发送方：`buyer`、`assistant`。
- 语言：`English`、`Filipino`、`Indonesian`、`Malay`、`Thai`、`Vietnamese`。

正式代码中的枚举名称使用大写成员名、保留上述小写或原始字符串值。公共基础枚举不得在本任务中重命名。

## 6. 外键删除策略

- `shops`、`products`、`skus`、`orders`：被引用时使用 `RESTRICT`，避免级联删除核心业务数据。
- `order_items`、`logistics_records`、`returns_refunds`：随业务对象归档，不提供公共硬删除接口。
- `logistics_tracks`、`customer_messages`：仅在内部维护或测试清理时允许随父记录 `CASCADE`。
- 生产式业务流程默认使用状态归档或软删除语义；删除重要数据仍须走待确认任务。

## 7. 索引与查询基线

- `products(shop_id, status, updated_at)`。
- `products(site, category_external_id)`。
- `skus(product_id, status)`。
- `inventory_records(sku_id, warehouse_external_id)` 唯一。
- `inventory_records(stock_status, updated_at)`。
- `orders(shop_id, order_status, source_created_at)`。
- `orders(buyer_external_id, source_created_at)`。
- `order_items(order_id)`、`order_items(product_id)`、`order_items(sku_id)`。
- `logistics_records(order_id)` 唯一、`logistics_records(tracking_number)` 唯一。
- `logistics_tracks(logistics_id, event_time)`。
- `returns_refunds(order_id, status)`。
- `reviews(product_id, source_created_at)`。
- `customer_sessions(status, source_created_at)`。
- `customer_messages(session_id, message_time)`。
- `category_trends(site, category_external_id, date)` 唯一。

所有列表 API 必须分页，不允许无界返回。

## 8. 导入顺序与事务

```text
shops
→ products
→ skus
→ inventory_records
→ orders
→ order_items
→ reviews
→ logistics_records
→ logistics_tracks
→ customer_sessions
→ customer_messages
→ returns_refunds
→ category_trends
```

- 导入前执行文件级 Schema、必填列、模拟标识和主键唯一性校验。
- 单次完整初始化在一个事务中执行；任一文件失败则回滚该批次。
- 重复执行使用 `external_id` 和业务唯一约束实现幂等，不重复插入。
- 默认不覆盖人工修改的数据；覆盖策略必须显式配置并记录导入批次。
- 导入是业务写操作，后续通过内部 Service 或受控 CLI 执行，不开放绕过服务层的公共任意文件写入接口。

## 9. 模块边界

### 成员二负责

- 数据 Schema、导入、清洗、来源和质量记录。
- 商品、SKU、库存、订单、物流和售后 Repository/Service/API。
- `PlatformAdapter` 结构化契约和 `MockShopeeAdapter`。
- 为成员三提供商品、评论和趋势只读查询。
- 为成员四提供商品、库存、订单、物流和客服会话只读查询。
- 与上述能力对应的成员二页面、测试和文档。

### 不属于成员二

- 智能选品评分、评论情感/主题算法和产品改良生成。
- Prompt、LLM 输出和商品内容生成。
- RAG、客服意图识别、回复生成和客服安全判断。
- Agent 总编排、公共权限框架、PPT 和软件著作权材料。

成员二可以提供底层数据和工具，但不得把其他成员的业务算法并入本模块。

## 10. 后续实现顺序

1. SQLAlchemy 模型和 Alembic 迁移。
2. CSV Pydantic Schema、导入 Repository/Service 和初始化 CLI。
3. 结构化 `PlatformAdapter` 请求/响应 Schema。
4. `MockShopeeAdapter` 只读商品、库存、订单、物流和消息能力。
5. 经待确认任务执行的商品、价格、库存和模拟上下架写操作。
6. 业务 API、经营统计、成员二页面和集成测试。

## 11. 本设计验收标准

- 12 个 CSV 均有明确目标表和字段映射。
- 主键、外键、唯一约束、金额和时间类型明确。
- 导入顺序与幂等策略明确。
- 模拟数据、来源追踪和脱敏边界明确。
- 成员二与成员三、成员四的共享数据边界明确。
- 不宣称任何业务表、导入能力或真实 Shopee 接口已经实现。

## 12. 待人工复核

当前执行环境缺少专用工作簿读取依赖，未直接解析 `data_dictionary.xlsx`。本设计依据与该工作簿同包发布的 CSV 表头、数据包 README、生成器和校验器完成。进入迁移实现前，应由成员二用 Excel 对照工作簿中的字段、枚举和关系页完成一次人工复核；发现差异时先更新本文档，再修改迁移。

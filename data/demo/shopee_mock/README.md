# 跨境电商智能体平台模拟实验数据包

> **重要声明：本目录中的全部业务记录均为模拟实验数据（`is_mock_data=true`），不来自真实 Shopee 店铺、买家、订单、评论或生产接口，不应被解释为平台真实经营数据。**

## 1. 数据背景

本数据包用于“跨境电商智能体平台”首版开发。首版采用“本地业务系统 + 公开数据结构参考 + 模拟实验数据 + MockShopeeAdapter”，不注册或调用真实 Shopee 生产账号与接口。数据以跨境电商常见业务对象为参考，覆盖商品、SKU、库存、订单、物流、评论、客服、售后和类目趋势。

固定随机种子为 `20260727`，因此在相同 Python 版本和脚本版本下可以复现同一套结果。

## 2. 文件清单与用途

| 文件 | 数据行数 | 主要用途 |
|---|---:|---|
| `products.csv` | 103 | 商品目录、选品基础信息、看板商品指标；含 3 个 Assistant 新加坡母婴演示候选 |
| `skus.csv` | 263 | SKU、规格、价格与成本 |
| `inventory.csv` | 263 | SKU 库存、预留库存、安全库存与库存状态 |
| `reviews.csv` | 1,000 | 多语言评论、情感分析、问题分类和产品改良 |
| `orders.csv` | 500 | 订单、支付和状态流转 |
| `order_items.csv` | 1,229 | 订单商品明细及金额核算 |
| `logistics.csv` | 443 | 订单物流单和最新物流状态 |
| `logistics_tracks.csv` | 1,711 | 物流轨迹事件，每单 2–6 条 |
| `customer_sessions.csv` | 100 | 客服会话、意图、风险级别和状态 |
| `customer_messages.csv` | 596 | 多轮买家与客服消息 |
| `returns_refunds.csv` | 50 | 退款、退货、原因和处理状态 |
| `category_trends.csv` | 2,880 | 6 个站点 × 8 个类目 × 连续 60 天趋势 |
| `data_dictionary.xlsx` | 15 个工作表 | 文件、字段、枚举和关联关系说明 |
| `mock_data_generator.py` | — | 一键重建全部 CSV |
| `validate_data.py` | — | 自动检查数据质量并生成报告 |
| `validation_report.md` | — | 最近一次完整校验结果 |

所有 CSV 均使用 UTF-8-SIG 编码，适合直接用 Excel、Python、数据库导入工具或文本编辑器打开。

## 3. 数据关系

```text
products.product_id
  ├─ skus.product_id
  ├─ order_items.product_id
  ├─ reviews.product_id
  └─ customer_sessions.product_id

skus.sku_id
  ├─ inventory.sku_id
  ├─ order_items.sku_id
  └─ reviews.sku_id

orders.order_id
  ├─ order_items.order_id
  ├─ reviews.order_id
  ├─ logistics.order_id
  ├─ customer_sessions.order_id
  └─ returns_refunds.order_id

logistics.tracking_number
  └─ logistics_tracks.tracking_number

customer_sessions.session_id
  └─ customer_messages.session_id

order_items.order_item_id
  └─ returns_refunds.order_item_id
```

核心主外键已通过 `validate_data.py` 验证。订单明细中的 `sku_id` 也与对应 `product_id` 保持一致。

## 4. 数据逻辑

- 商品和 SKU 售价不低于合理成本，SKU 价格围绕商品基础价格波动。
- 商品销量、收藏量、评论量和评分采用相关但非完全相同的模拟逻辑。
- 订单总额满足：`total_amount = subtotal + shipping_fee - discount_amount`。
- 待付款订单没有付款或发货时间；取消订单没有完成时间。
- 已付款及后续状态订单均有物流单，待付款订单没有物流单。
- 每个物流单含 2–6 条按时间递增的轨迹。
- 评论评分与 `sentiment_hint` 一致，覆盖六种语言和八类负面问题。
- 每条评论原文与 `content_zh` 均由成对的合成模板生成，中文内容逐条对应原文语义，不使用随机情绪摘要冒充翻译。
- 每个商品拥有独立的质量画像和非均匀评论数量；同一商品同时保留正面、中性和负面体验证据，负面问题按商品类目约束。
- 库存状态由可用库存与安全库存确定；库存值均为非负整数。
- 趋势包含持续增长、激烈竞争、下降、季节波动和价格上涨/销量下降等模式。

## 5. 重新生成数据

只需要 Python 3.10 或更高版本，生成 CSV 不依赖第三方库：

```bash
python mock_data_generator.py
```

脚本会覆盖本目录中的 12 个 CSV。运行前如需保留人工修改，请先复制备份。

若未来版本改用 `pandas` 或 `faker`，可安装：

```bash
python -m pip install pandas faker
```

当前脚本无需安装这两个包。

## 6. 执行数据校验

```bash
python validate_data.py
```

校验内容包括：

- 文件与必填列；
- 主键唯一性和外键有效性；
- 模拟数据标识；
- 商品价格/成本；
- 库存非负值及状态；
- 订单明细与订单金额；
- 订单、支付和物流状态；
- 评论评分与情感；
- 物流轨迹顺序与数量；
- 客服多轮消息；
- 趋势时间连续性。

成功时脚本退出码为 `0`，存在失败项时退出码为 `1`，并始终更新 `validation_report.md`。

## 7. 数据库导入

### SQLite

SQLite 命令行中可逐表导入：

```sql
.mode csv
.headers on
.import --skip 1 products.csv products
.import --skip 1 skus.csv skus
.import --skip 1 inventory.csv inventory
```

其余文件使用相同方式导入。正式开发时建议先依据 `data_dictionary.xlsx` 创建表结构、主键和外键，再进行导入。

### MySQL

先创建 UTF-8 数据库和表，再使用：

```sql
LOAD DATA LOCAL INFILE 'products.csv'
INTO TABLE products
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
```

Windows 环境若出现换行差异，可改用 `LINES TERMINATED BY '\r\n'`。金额建议使用 `DECIMAL`，时间建议使用支持时区的应用层解析或统一转换为 UTC 后保存。

### 其他数据库

PostgreSQL 可使用 `COPY`/`\copy`，SQL Server 可使用导入向导或 `BULK INSERT`。建议导入顺序：

1. `products`
2. `skus`
3. `inventory`
4. `orders`
5. `order_items`
6. `reviews`
7. `logistics`
8. `logistics_tracks`
9. `customer_sessions`
10. `customer_messages`
11. `returns_refunds`
12. `category_trends`

## 8. 团队使用建议

- **成员一（底座、Agent、权限与集成）**：可用订单状态、Mock 工具输入输出、审批测试、日志和演示初始化；可把 CSV 导入统一数据库。
- **成员二（数据、适配器与业务后台）**：负责全量数据、商品/SKU/库存/订单/物流接口、统计服务与 `MockShopeeAdapter`。
- **成员三（选品和内容 AI）**：重点使用 `products.csv`、`reviews.csv`、`category_trends.csv`、成本、价格和销量字段。
- **成员四（客服、RAG 与前端）**：重点使用商品/库存/订单/物流数据以及 `customer_sessions.csv`、`customer_messages.csv`。

## 9. MockShopeeAdapter 使用建议

适配器应读取统一业务实体，而不是让上层 Agent 直接依赖 CSV 字段。建议建立仓储层并暴露：

- `get_shop_info`
- `list_products` / `get_product`
- `create_product_draft` / `publish_product` / `update_product`
- `update_price` / `update_inventory`
- `list_orders` / `get_order`
- `get_logistics`
- `get_chat_messages` / `send_chat_reply`

切换真实平台时，仅替换适配器和认证/限流实现，上层服务继续使用统一接口。

## 10. 当前限制

- 数据仅覆盖演示级规模，不代表任何站点的真实市场份额或成交情况。
- 汇率未做跨币种统一换算；不同站点价格应在本地货币内分析。
- 客服非英语消息使用语言标记和受控模板，适合流程/RAG测试，不用于语言模型基准测试。
- 评论与订单是有限窗口样本；同一已完成订单可能出现补充型评价记录。
- 评论及中文内容仍是人工设计规则生成的合成数据，不是机器翻译结果或真实消费者原话；适合功能演示和确定性测试，不适合评价真实翻译模型质量。
- 未包含真实图片、地址、手机号、邮箱、支付凭据、Partner ID 或 Partner Key。
- 未模拟全部平台错误码、税费、优惠券和复杂拆单场景。

## 11. 替换为真实数据的方法

未来取得合法权限后，应新增 `RealShopeeAdapter` 或第三方市场数据适配器：

1. 将真实响应转换为本数据字典中的统一实体；
2. 保留 `source_type`、采集时间、站点、币种和数据版本；
3. 将 `is_mock_data` 设为 `false`，并与模拟数据物理或逻辑隔离；
4. 在进入分析层前执行同一套清洗、校验和脱敏；
5. 对真实接口增加认证、签名、限流、重试和审计；
6. 不修改成员三、成员四依赖的上层业务接口。

## 12. 合规说明

本数据包未抓取或复制受登录、验证码或平台安全措施保护的数据，不含真实个人信息或生产凭据。它仅用于课程项目、软件开发、自动化测试和答辩演示。若未来采集公开数据，应遵守目标网站条款、robots 规则、适用法律、合理请求频率和数据最小化原则；不得绕过验证码、登录验证或其他访问控制。

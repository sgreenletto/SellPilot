# 模拟数据校验报告

- 校验状态：**通过**
- 通过项：101
- 警告项：0
- 失败项：0
- 数据性质：全部为模拟实验数据，不代表真实 Shopee 生产数据。

## 文件数量

| 文件 | 数据行数 |
|---|---:|
| products.csv | 100 |
| skus.csv | 260 |
| inventory.csv | 260 |
| reviews.csv | 1000 |
| orders.csv | 500 |
| order_items.csv | 1239 |
| logistics.csv | 451 |
| logistics_tracks.csv | 1821 |
| customer_sessions.csv | 100 |
| customer_messages.csv | 584 |
| returns_refunds.csv | 50 |
| category_trends.csv | 2880 |

## 通过项

- products.csv contains required columns
- products.csv loaded: 100 data rows
- skus.csv contains required columns
- skus.csv loaded: 260 data rows
- inventory.csv contains required columns
- inventory.csv loaded: 260 data rows
- reviews.csv contains required columns
- reviews.csv loaded: 1000 data rows
- orders.csv contains required columns
- orders.csv loaded: 500 data rows
- order_items.csv contains required columns
- order_items.csv loaded: 1239 data rows
- logistics.csv contains required columns
- logistics.csv loaded: 451 data rows
- logistics_tracks.csv contains required columns
- logistics_tracks.csv loaded: 1821 data rows
- customer_sessions.csv contains required columns
- customer_sessions.csv loaded: 100 data rows
- customer_messages.csv contains required columns
- customer_messages.csv loaded: 584 data rows
- returns_refunds.csv contains required columns
- returns_refunds.csv loaded: 50 data rows
- category_trends.csv contains required columns
- category_trends.csv loaded: 2880 data rows
- products.csv primary key product_id is unique
- products.csv required fields are complete
- products.csv mock-data flag is complete
- skus.csv primary key sku_id is unique
- skus.csv required fields are complete
- skus.csv mock-data flag is complete
- inventory.csv primary key inventory_id is unique
- inventory.csv required fields are complete
- inventory.csv mock-data flag is complete
- reviews.csv primary key review_id is unique
- reviews.csv required fields are complete
- reviews.csv mock-data flag is complete
- orders.csv primary key order_id is unique
- orders.csv required fields are complete
- orders.csv mock-data flag is complete
- order_items.csv primary key order_item_id is unique
- order_items.csv required fields are complete
- order_items.csv mock-data flag is complete
- logistics.csv primary key logistics_id is unique
- logistics.csv required fields are complete
- logistics.csv mock-data flag is complete
- logistics_tracks.csv primary key track_id is unique
- logistics_tracks.csv required fields are complete
- logistics_tracks.csv mock-data flag is complete
- customer_sessions.csv primary key session_id is unique
- customer_sessions.csv required fields are complete
- customer_sessions.csv mock-data flag is complete
- customer_messages.csv primary key message_id is unique
- customer_messages.csv required fields are complete
- customer_messages.csv mock-data flag is complete
- returns_refunds.csv primary key return_id is unique
- returns_refunds.csv required fields are complete
- returns_refunds.csv mock-data flag is complete
- category_trends.csv primary key trend_id is unique
- category_trends.csv required fields are complete
- category_trends.csv mock-data flag is complete
- skus.csv.product_id references valid products.csv
- inventory.csv.sku_id references valid skus.csv
- reviews.csv.product_id references valid products.csv
- reviews.csv.sku_id references valid skus.csv
- reviews.csv.order_id references valid orders.csv
- order_items.csv.order_id references valid orders.csv
- order_items.csv.product_id references valid products.csv
- order_items.csv.sku_id references valid skus.csv
- logistics.csv.order_id references valid orders.csv
- logistics_tracks.csv.tracking_number references valid logistics.csv
- customer_sessions.csv.order_id references valid orders.csv
- customer_sessions.csv.product_id references valid products.csv
- customer_messages.csv.session_id references valid customer_sessions.csv
- returns_refunds.csv.order_id references valid orders.csv
- returns_refunds.csv.order_item_id references valid order_items.csv
- Order item SKU-to-product relationships are consistent
- Product currencies match their sites
- Product prices are reasonable relative to cost
- SKU prices are not below SKU cost
- Inventory quantities are non-negative
- Inventory status matches available and safety stock
- Order item subtotals are correct
- Order amounts reconcile to detail lines, fees, and discounts
- Order timestamps and status transitions are coherent
- Paid and post-payment orders have logistics records
- Pending-payment orders have not entered logistics
- Review ratings align with sentiment hints
- Review text has meaningful multilingual diversity
- Chinese review translations have meaningful per-item diversity
- Identical source reviews map to one consistent Chinese translation
- Every product has linked review evidence
- Every product includes both positive and negative review evidence
- Per-product review counts follow a non-uniform long-tail distribution
- Reviews match the buyer and item in their linked order
- Product review counts and average ratings reconcile to reviews
- Logistics track timestamps increase within each tracking number
- Each logistics record has 2–6 track events
- Returns match their order item and buyer
- Refund-status orders have after-sales records
- Customer sessions contain multi-turn conversations
- Category trends cover 60 ordered daily observations per site/category

## 警告项

- 无

## 失败项

- 无

# Mock Commerce 只读 API

所有接口位于 `/api/v1/commerce`，需要 Bearer 登录认证，数据来自数据库中的合成模拟记录。

- `GET /products`：商品列表；支持 `status`、`site`、`offset`、`limit`。
- `GET /products/{product_id}`：按稳定外部标识查询商品。
- `GET /orders`：订单列表；支持 `status`、`offset`、`limit`。
- `GET /orders/{order_id}`：订单详情。
- `GET /orders/{order_id}/logistics`：物流单及按时间排序的轨迹。
- `GET /messages`：消息列表；支持 `session_id` 和 `limit`。
- `GET /inventory`：库存列表；支持库存状态筛选和分页。
- `GET /returns`：退货退款列表；支持状态筛选和分页。

列表均设置上限，不允许无界返回。当前未开放创建商品、改价、库存调整、上下架或发送消息；这些写操作必须在后续通过内部 Service 创建待确认任务，确认成功后才能调用适配器执行。

`RealShopeeAdapterStub` 仍不连接真实 Shopee，也不会回退到 Mock。

## 待确认写操作

- `POST /products/{product_id}/publish-request`
- `POST /products/{product_id}/unpublish-request`
- `POST /products/{product_id}/price-request`
- `POST /products/{product_id}/inventory-request`

这些接口只创建内部 `AgentTask` 和 `ConfirmationTask`，不会立即修改业务数据。用户随后调用既有的 `POST /confirmations/{id}/confirm`，系统注册对应 Commerce 执行器后才修改 Mock 数据，并写入操作前后快照、执行结果和 `OperationLog`。重复幂等键返回原确认任务，重复确认不会再次执行。
## 经营看板前端聚合

经营看板当前不新增独立的 Dashboard 后端接口，而是通过统一 API 客户端分页读取以下已有只读接口：

- `GET /v1/commerce/products`
- `GET /v1/commerce/inventory`
- `GET /v1/commerce/orders`

前端基于完整分页结果汇总商品总数、低库存、订单趋势、上架状态及热销商品等展示数据。接口连接失败、鉴权失效或服务不可用时，页面不会显示为空白，而会明确提示“后端未连接”，并回退到带有 Mock 标识的合成演示数据。

客服会话、任务、提醒和部分趋势目前没有对应的经营看板聚合接口，因此页面必须明确标记为“未接入”或“合成演示”，不得将其描述为后端真实数据。

经营看板的数据范围选择器使用数据包保留的来源店铺标识 `SHOP001` 至 `SHOP006`。商品、库存和订单列表接口均接受可选的 `shop_id` 查询参数；该参数匹配 `source_shop_external_id`，不会把站点字段冒充为店铺字段。“全部模拟店铺”不传该参数，用于汇总所有来源店铺。

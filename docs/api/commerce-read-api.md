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

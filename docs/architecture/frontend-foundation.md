# Frontend Foundation Architecture

## 状态与范围

本文描述 SellPilot `0.1.0` Foundation Milestone 的前端公共底座。它包含布局、设计变量、组件库、路由、公共状态、API 客户端与经营看板展示，不代表任何跨境电商业务模块已经完成或已用于生产。

## 分层

```text
View
  → Sp 公共组件 / 图表组件
  → composable / Pinia
  → api/http.ts
  → FastAPI /api/v1
```

- View 负责组合页面，不直接使用 `fetch`，不创建 ECharts 实例。
- `components/base` 保持无业务数据，提供交互和视觉原语。
- `components/data-display` 与 `components/ai` 只负责展示契约。
- `components/charts` 管理 ECharts 初始化、响应式 resize 与销毁。
- `config/navigation.ts` 是侧边导航唯一配置来源。
- `stores/app.ts` 只保存侧边栏、页面标题和平台状态等公共状态。
- `mocks/dashboard.ts` 保存 Dashboard 合成演示数据，避免与 View 混合。

Dashboard 在后端可用时按当前店铺重新计算商品运营漏斗，阶段依次为“店铺商品 → 资料完整
→ 库存健康 → 健康且已上架”。库存健康表示可用库存高于安全阈值且未标记为低库存。
后续阶段只统计满足前序阶段条件的商品，避免把浏览器会话中的选品
候选、草稿状态和在售状态误当作同一条转化链路。曲线使用当前店铺各阶段的实际数量，
不对不同店铺做平均或补齐；阶段按包含关系递减，避免出现末段反弹的 U 形误导。

“上架与库存”页面在后端可用时复用同一店铺范围的商品与库存查询。商品列表中的“后端 Mock
状态”用于核对 Dashboard 统计。Mock 上下架采用两步确认：首次操作创建内部 ConfirmationTask，
用户再次确认后才由后端 CommerceOperationService 调用平台适配器修改 Mock 数据库并记录日志；
取消确认不会修改状态。后端读取失败时不使用未过滤的本地 CSV 冒充当前店铺数据。

Dashboard 的“异常提醒与今日待办”不使用固定商品名称。当前只根据所选店铺后端返回的低库存
记录、待支付订单以及与当前商品关联的待确认任务生成提醒。客服和物流提醒在缺少可按店铺核验
的关联查询时不显示；无可核验记录时展示空状态，不回退到硬编码演示提醒。

商品管理和订单履约列表按顶部所选来源店铺读取后端分页聚合数据；订单商品明细、物流、售后和
客服关联继续使用同一合成 Mock 数据包按稳定订单 ID 补充。库存单项和批量调整必须先创建待确认
任务，再由用户确认后写入 Mock 数据库。Dashboard 在评论情绪和客服趋势缺少店铺级接口时展示
空状态，不显示固定趋势曲线。

## API 与错误

`api/http.ts` 读取 `VITE_API_BASE_URL`，提供超时、统一响应解包和 `FrontendApiError`。开发环境 `/api` 由 Vite 代理到 `VITE_PROXY_TARGET`。

平台状态只通过 `GET /api/v1/platform/status` 获取。接口失败时清空状态并展示“后端未连接”，不允许静默构造 Mock 成功结果。

## 路由与加载

应用壳通过路由 `meta.keepAlive` 仅缓存智能选品、评论分析、产品改良和内容工坊四个有长耗时
分析或生成交互的工作台，缓存上限为 4。用户在站内切换页面时，进行中的 Promise、表单状态和
已返回结果不会随路由组件卸载而丢失。普通查询页不缓存；浏览器刷新后的事实恢复仍由后端
PostgreSQL 中的任务、候选清单、确认任务和内容版本负责，不把大型业务结果写入
`localStorage`。

公共路由使用 `DefaultLayout`。未实现业务模块复用 `ModulePlaceholderView`，页面名称、模块和说明来自路由元数据。`/tasks` 已替换为真实 `TaskCenterView`，复用现有 Sp 组件与语义变量：列表只取任务摘要，选中任务后并行按需读取详情、Step、ToolCall、Confirmation 和 OperationLog。操作按钮只渲染后端 `available_actions`，危险确认使用显式二次确认，成功后刷新列表与详情，并通过查询参数恢复选中任务。`/dev/design-system` 仅在开发构建中注册。

`api/tasks.ts` 复用统一认证 HTTP Client 和响应包络，过滤空查询参数，并将 404、409、
422 转换为任务中心的安全提示；401 继续由统一客户端处理登录失效。页面不展示内部运行字段，
不使用硬编码任务或结果数据，也不引入新的 Drawer、Dialog 或表格设计系统。

## 响应式

- `>= 1280px`：Dashboard 为漏斗与 AI 卡双列。
- `1024px–1279px`：AI 卡移动到漏斗下方。
- `< 1024px`：侧边栏成为抽屉。
- `< 768px`：内容单列，工具栏重排，风险表可横向滚动。

AppShell 在视口内保持固定高度，主工作区独立纵向滚动；侧边栏菜单在超高时独立滚动，用户区保持在底部。布局不依赖固定画布，并全局尊重 `prefers-reduced-motion`。

## 真实边界

- Dashboard 数据为合成 Mock 数据，不是实际店铺数据。
- `MockShopeeAdapter` 的真实状态由后端返回；前端不复制业务适配器。
- `RealShopeeAdapterStub` 只表示未配置占位，不代表连接 Shopee。
- AI Orb 是本地 SVG/CSS 视觉组件；“生成运营报告”不调用模型。

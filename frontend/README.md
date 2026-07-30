# SellPilot Frontend Foundation

成员二的市场数据、商品管理、上架库存和订单履约页面已接入项目 Mock
数据包。功能状态及后端边界见
[`docs/requirements/member2-frontend-acceptance.md`](../docs/requirements/member2-frontend-acceptance.md)。

SellPilot 前端采用 Vue 3、TypeScript 与 Vite，当前正式版本为 `1.0.0`。`v0.5.0`
保留为 AI 运营助手与跨模块工作流集成的历史里程碑。

## 当前边界

当前已实现公共布局、可复用组件、统一 API 客户端、经营看板、Mock 商品/订单/库存页面、
中文聊天式 AI 运营助手、任务中心，以及智能选品、评论分析、产品改良、内容生成、知识检索和客服工作台。

v1.0.0 发布说明见
[`docs/release/v1.0.0-release-notes.md`](../docs/release/v1.0.0-release-notes.md)；当前不连接
真实 Shopee。

平台标签会请求后端 `/api/v1/platform/status`。请求失败时界面显示“后端未连接”，不会伪装成 Mock Shopee 正常运行。

## 技术栈

- Vue 3 Composition API 与 `<script setup>`
- TypeScript 严格模式、Vite
- Vue Router、Pinia
- Element Plus 基础反馈与浮层能力
- ECharts、@lucide/vue
- ESLint、Prettier、Vitest、Vue Test Utils、jsdom

## 安装与运行

要求 Node.js 兼容当前锁文件，并使用 npm：

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

生产构建和本地预览：

```bash
npm run build
npm run preview
```

代码检查：

```bash
npm run format
npm run format:check
npm run lint
npm run typecheck
npm run test:run
```

## 环境配置

复制 `frontend/.env.example` 为仅本地使用的 `.env`：

```dotenv
VITE_API_BASE_URL=/api
VITE_PROXY_TARGET=http://127.0.0.1:8000
```

使用仓库根目录 `start-sellpilot.bat` 时不需要手工同步该值：启动器会根据后端
`API_HOST` / `API_PORT` 配置注入同一代理目标。仅单独运行前端时才需要在本地环境中
设置 `VITE_PROXY_TARGET`。

开发服务器把 `/api` 代理到 FastAPI。`VITE_*` 会暴露给浏览器，禁止放入密码、Token 或 API Key。

## 目录

| 路径                           | 用途                                  |
| ------------------------------ | ------------------------------------- |
| `src/api/`                     | 统一 HTTP、错误对象和平台状态接口     |
| `src/components/base/`         | 无业务数据的 `Sp` 基础组件            |
| `src/components/layout/`       | Shell、侧边栏、顶部栏与页面容器       |
| `src/components/data-display/` | 指标、状态、风险与表格展示            |
| `src/components/charts/`       | ECharts 生命周期封装                  |
| `src/components/ai/`           | 原创 Orb 与当前无真实 AI 调用的展示卡 |
| `src/config/`                  | 导航配置                              |
| `src/mocks/`                   | 明确标识的 Dashboard 合成数据         |
| `src/router/`                  | 路由与页面元数据                      |
| `src/stores/`                  | 公共 Pinia 状态                       |
| `src/styles/`                  | 语义变量、重置、全局与覆盖样式        |
| `src/views/`                   | Dashboard、开发展示页和统一占位页     |
| `tests/`                       | 不依赖后端或外网的组件与页面测试      |

## 路由

- `/dashboard`：完整经营看板。
- `/assistant`
- `/market/data`
- `/market/selection`：正式智能选品工作台。
- `/market/reviews`
- `/products`
- `/products/content`
- `/products/listing-inventory`
- `/customer-service/conversations`
- `/customer-service/knowledge`
- `/orders`
- `/tasks`

未列为已实现的业务路由仍复用统一占位页，不表示对应业务已完成。

## 设计变量与组件原则

所有页面使用 `src/styles/tokens.css` 的 `--sp-*` 语义变量。颜色、间距、圆角、阴影、字号和过渡不得在 View 中重复硬编码。

- 优先使用 `SpButton`、`SpInput`、`SpSelect`、`SpCard` 等公共组件。
- 组件 props 和 emits 必须有严格 TypeScript 类型，禁止 `any`。
- Element Plus 只在公共封装或必要的反馈能力中使用，业务页不得堆叠原始 Element Plus 组件。
- View 不直接调用 `fetch`，统一通过 `src/api/http.ts`。
- View 不创建 ECharts 实例，统一由图表组件管理 resize 和 dispose。
- 状态不能只依靠颜色表达，交互必须保留键盘焦点。

详细规范见 `docs/frontend/design-system.md`。

## Dashboard 数据

漏斗、运营指标、健康曲线和高风险事项来自 `src/mocks/dashboard.ts`，均为带稳定 ID 的合成数据。商品行明确标注“模拟商品”，报告按钮只显示未接入提示，不调用 AI 或消耗模型 Token。

## 当前未实现

- 真实登录和复杂权限。
- 真实商品、订单、库存、物流、客服或知识库页面。
- 评论分析、内容生成与完整 Agent 页面。
- 全局搜索、正式报告生成和真实 Shopee 连接。
- Docker Compose、CI/CD 与生产部署。

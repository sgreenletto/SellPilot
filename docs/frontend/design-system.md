# SellPilot Frontend Design System

## 视觉语言

界面采用低饱和蓝灰背景、大圆角应用容器和浅色玻璃卡片。主操作使用深海军蓝，玫红与亮蓝只作为少量强调。设计不依赖远程字体、图片或参考图中的品牌素材。

## 设计变量

变量统一位于 `frontend/src/styles/tokens.css`。

| 类别 | 主要变量 |
| --- | --- |
| 背景与表面 | `--sp-color-bg`、`--sp-color-shell`、`--sp-color-surface` |
| 文本 | `--sp-color-text`、`--sp-color-text-secondary`、`--sp-color-text-muted` |
| 品牌与状态 | `--sp-color-primary`、`--sp-color-accent-pink`、`--sp-color-accent-blue`、成功/警告/危险 |
| 间距 | `--sp-space-1` 到 `--sp-space-12`，基于 4px 递进 |
| 圆角 | shell 32px、card 24px、small card 18px、control 15px、pill |
| 阴影 | `--sp-shadow-shell`、`--sp-shadow-card`、`--sp-shadow-hover` |
| 字体 | Inter、Manrope、苹方、微软雅黑与系统字体回退 |
| 动效 | `--sp-transition-fast`、`--sp-transition-normal` |

所有 View 禁止直接硬编码十六进制颜色、复制阴影值或建立另一套间距。需要新语义时先扩展 token。

## 组件命名

公共组件统一使用 `Sp` 前缀：

- 基础：`SpButton`、`SpIconButton`、`SpInput`、`SpSelect`、`SpBadge`、`SpAvatar`、`SpCard`、`SpEmptyState`、`SpSkeleton`。
- 数据展示：`MetricItem`、`MetricStrip`、`RiskIndicator`、`StatusBadge`、`PlatformModeBadge`、`RiskOperationsTable`。
- 布局：`AppShell`、`AppSidebar`、`AppTopbar`、`PageContainer`。
- 图表和 AI 展示：`OperationsFunnelChart`、`MiniHealthChart`、`AiOrb`、`AiCopilotCard`。

## 页面开发规范

1. 使用 Composition API、`<script setup>` 和严格 TypeScript。
2. View 组合公共组件，不直接大量使用 Element Plus。
3. Element Plus 仅用于公共封装或确有必要的消息、浮层等能力。
4. 导航由 `config/navigation.ts` 驱动。
5. HTTP 请求通过 `api/http.ts`，API 错误转换为统一前端错误。
6. ECharts 只能在图表组件内初始化，并实现 resize 与 dispose。
7. 列表必须有稳定 ID；大型 Mock 数据放入 `mocks`。
8. 状态必须同时使用文字、图标或结构表达，不能只依靠颜色。
9. 所有交互提供 `focus-visible`，并尊重 reduced motion。
10. 不使用远程图片，不复制参考图 Logo、头像、Orb 或业务文案。

## 团队使用方式

开发时先打开 `/dev/design-system` 查看已支持的组件状态与组合方式。优先复用现有组件；确有跨页面复用价值时再扩展公共组件，并同步添加测试与本文说明。开发展示路由不会进入生产导航。

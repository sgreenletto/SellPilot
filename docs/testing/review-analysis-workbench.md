# 评论分析前端测试

专项测试覆盖筛选参数与鉴权、评论及翻译缺失状态、创建并运行分析、规则模式标识、
代表证据定位、后端断连和空数据。趋势组件独立管理 ECharts 生命周期。

```powershell
cd frontend
npx vitest run tests/unit/review-analysis-api.spec.ts tests/unit/review-analysis-view.spec.ts
npm run build
```

最新 `develop` 仍有其他前端模块的既有类型、Lint 和 PlatformModeBadge 测试问题，
不在本功能分支中混入无关修复。

# 评论分析工作台

```text
ReviewAnalysisView
→ review-analysis API client
→ unified HTTP client
→ Step 6 ReviewAnalysis API
```

View 不直接调用 `fetch` 或创建 ECharts。趋势图由 `ReviewTrendChart` 封装并在卸载时
释放实例，筛选、进度、错误、空数据和证据分页均使用后端真实状态。

页面覆盖评论原文和已有翻译、情感分布、主题与痛点、五类问题、时间与站点趋势、
代表评论及点击定位。产品改良只提供 Step 8 入口，不伪造未实现的报告。

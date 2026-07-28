# 智能选品 API

全部端点位于 `/api/v1/selection`，要求 Bearer Token。

## 候选查询

`GET /candidates` 支持 `site`、`category_id`、`min_price`、`max_price`、`sort_by`、
`descending`、`offset` 和 `limit`。

## 创建分析

`POST /analyses` 接收候选查询字段以及：

- `minimum_profit`
- `minimum_margin`
- `platform_fee_rate`
- `other_costs`
- `cost_override`（可选）
- `shipping_cost_override`（可选）
- `product_weight_kg`（可选）
- `risk_preference`：`conservative`、`balanced` 或 `growth`

成本与物流覆盖值进入确定性利润公式。重量记录在任务条件中；当前无重量运费阶梯，不影响评分。
风险偏好选择版本化权重配置。响应包含任务 ID、公式版本、排名、利润、分项证据、解释、风险提示、
排除项和 Mock 标记。

## 任务、对比和导出

- `GET /analyses/{task_id}`
- `GET /analyses/{task_id}/compare?product_id=...`
- `GET /analyses/{task_id}/export`

详情、对比和导出校验任务所有权。导出返回 JSON 内容、文件名和 SHA-256，不在服务器创建文件。

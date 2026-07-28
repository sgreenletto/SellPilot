# 成员三 AI 能力评估报告

- 数据集版本：`member3-eval-v1.0.0`
- 评估器版本：`member3-evaluator-v1.0.0`
- 实际运行时间：`2026-07-28T10:15:39.572461+00:00`
- 总耗时：`9.567 ms`
- 失败案例：`0`

## 实际指标

### selection

- calculation_correct_rate: `1.0`
- ranking_stability_rate: `1.0`
- formula_version: `selection-v1.0.0`
- case_count: `2`

### review_analysis

- sentiment_correct_rate: `1.0`
- topic_correct_rate: `1.0`
- evidence_reference_valid_rate: `1.0`
- analysis_origin: `rule`
- analyzer_version: `review-analysis-v1.0.0`
- case_count: `3`

### content_generation

- structured_output_success_rate: `1.0`
- fact_consistency_rate: `1.0`
- hallucination_rate: `0.0`
- multilingual_schema_score: `1.0`
- repeat_stability_rate: `1.0`
- compliance_detection_accuracy: `1.0`
- detected_claim_count: `1`
- provider: `offline_template`
- model_name: `sellpilot-localized-template-v1`
- prompt_version: `offline-template-v1`
- token_usage: `not_applicable_offline_provider`
- estimated_cost: `not_applicable_offline_provider`
- case_count: `2`

## 失败案例

本次固定评估集未发现失败案例。评估器不会隐藏后续新增案例的失败。
## 边界说明

- 数据全部为固定合成数据，不包含真实用户或店铺数据。
- 内容生成使用明确标记的 `offline_template`，未冒充真实 LLM。
- 离线提供方没有 Token 和计费，因此相关字段记录为不适用，不伪造数值。

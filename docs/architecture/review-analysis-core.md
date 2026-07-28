# 评论分析内核

## 范围

本阶段实现 `sellpilot.domain.review_analysis` 纯领域内核，接收经过 Schema 校验的评论集合，输出可重新计算、可追踪证据的结构化分析结果。

本阶段不包含数据库写入、Service、API、Tool、Workflow、前端页面或产品改良报告；这些能力分别属于后续 Step 6—Step 8。内核不直接读取 CSV、数据库或 `MockShopeeAdapter`，来源评论由调用方通过正式 `ReviewInput` 契约传入。

## 流程

```text
ReviewInput
→ 文本规范化和质量检查
→ 声明语言与检测语言核对
→ 使用已有译文或明确标记翻译不可用
→ 评分驱动的确定性情感判断
→ 多语言受控主题分类
→ 高频关键词、主题、负向痛点、情感和证据聚合
→ 站点/月度趋势
→ ReviewAnalysisReport 交叉校验
```

默认规则内核不调用 LLM。可选 `ReviewModel` 仅是结构化增强接口，必须返回完整批次的 `review_id`、情感、受控主题和置信度。非法 JSON、未知主题、重复、未知或缺失证据 ID、空结果、异常和超时均失败关闭，不生成伪成功报告。

## 受控主题

- `product_quality`
- `packaging`
- `description_mismatch`
- `logistics`
- `service`
- `material`
- `size_specification`
- `wrong_or_missing_item`
- `other`
- `no_clear_issue`

主题覆盖产品质量、包装、描述不符、物流、服务、材料、尺寸规格和错发漏发。输入中的 `sentiment_hint` 与 `issue_type` 是模拟实验提示，不能覆盖评分事实或绕过输出校验。

## 证据和来源

- 每个非空主题聚合至少包含一个输入集合内的稳定 `review_id`。
- 痛点只由负向评论聚类形成，输出负向频次、严重度、影响站点和代表证据。
- 高频关键词由输入文本中受控主题词的实际命中次数生成，并保存命中的评论 ID。
- 证据保留原文、可选译文、检测语言、评分、评论时间、情感和置信度。
- `origin` 区分规则判断和模型判断；聚合数字属于可重算统计事实。
- 原文不会因分析长度限制被覆盖；超长文本只截断分析副本，并记录 `truncated`。
- 空文本、纯表情、垃圾文本和重复文本被排除并进入质量报告。
- 未知语言、语言不一致和翻译不可用被明确标记，不伪造翻译。
- 来源沿用 `SourceMetadata`，Mock 数据必须显式 `is_mock=true`。

## 站点隔离与趋势

趋势以 `(site, YYYY-MM)` 分组，输出评论数、差评数、平均评分和主题计数。不同站点不会合并成同一个趋势点；聚合值全部可由 `judgements` 重新计算。

## 后续接入

Step 6 应通过成员二评论 Repository 查询并分页读取来源评论，转换成 `ReviewInput` 后调用本内核，再由内部 Service 创建和持久化 `ReviewAnalysisResult` 与 `ReviewAnalysisEvidence`。API 路由不得直接调用 Repository 或自行拼装分析结果。

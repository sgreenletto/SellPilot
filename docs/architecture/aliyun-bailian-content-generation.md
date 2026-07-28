# 阿里云百炼内容生成接入

商品内容生成支持两种明确区分的模型模式：

- `offline_template`：默认模式，使用确定性离线模板，不访问外网，也不表示真实 LLM 已接入。
- `aliyun_bailian`：通过阿里云百炼 OpenAI 兼容接口调用真实模型。

## 本地配置

复制根目录 `.env.example` 为 `.env`，然后在本地填写：

```dotenv
CONTENT_MODEL_PROVIDER=aliyun_bailian
DASHSCOPE_API_KEY=
BAILIAN_BASE_URL=
BAILIAN_MODEL=qwen-plus
BAILIAN_TIMEOUT_SECONDS=30
```

`DASHSCOPE_API_KEY` 填写百炼控制台创建的 API Key。`BAILIAN_BASE_URL` 必须填写
创建该 Key 的工作空间和地域所显示的准确 API Host，并以
`/compatible-mode/v1` 结尾。不同地域和工作空间的地址可能不同，不能在代码中猜测。

`.env` 已被 Git 忽略。密钥不得写入 `.env.example`、前端 `VITE_*` 变量、日志、截图、
测试或提交记录。

## 调用与校验

百炼网关调用 `POST {BAILIAN_BASE_URL}/chat/completions`，使用 Bearer Token，
并请求 `response_format={"type":"json_object"}`。提示词同时包含：

- 通过平台适配器读取的已验证 Mock 商品事实；
- `LocalizedListing` 的 JSON Schema；
- 上一轮事实、合规和完整性检查问题。

响应必须先经过 JSON 解析和 Pydantic `LocalizedListing` 严格校验，之后才能进入最多
三轮的事实、关键词、SKU、语言、禁用宣称和完整性检查。HTTP 错误、无效 JSON 或
Schema 不匹配均明确失败，不会静默改用离线模板，也不会伪造真实模型成功。

调用记录保存 provider、model、状态、耗时及百炼返回的 token usage。由于仓库未配置
随时间变化的模型价格表，费用估算仍为零，不能解释为免费调用。

## 业务边界

百炼只负责生成结构化商品文案，不代表真实 Shopee 已接入。商品事实仍通过平台适配器
读取；保存草稿和恢复版本仍必须先创建 `ConfirmationTask`，确认前不会写入版本，
也不会发布商品、修改价格或库存。

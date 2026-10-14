# Decision 001：外部生成模型的数据边界

## Status

Accepted for configurable local MVP.

## Decision

- 外部模型默认关闭；只有同时配置 `OPENAI_API_KEY` 和 `OPENAI_MODEL` 才启用。
- 每次调用只发送用户当前问题和当前课程检索得到的最多三个片段。
- 不发送完整教材、其他课程资料、原始文件路径、历史对话或学习记录。
- API 密钥只从环境变量读取，不保存到数据库、日志或 Git。
- Responses API 请求设置 `store=False`。
- 外部调用失败时退回本地 extractive answer，并继续显示原始引用。

## Consequences

生成讲解需要用户自行提供有效的 API 账户、密钥和可用模型 ID。未配置时产品仍可完成检索和依据展示。

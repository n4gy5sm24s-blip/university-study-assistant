# Model Configuration API

## `GET /api/model`

返回本机模型是否已经配置、供应商和模型 ID。永远不返回 API Key 或其掩码片段。

## `PUT /api/model`

请求：`{"api_key": "...", "model": "gpt-6-luna"}`。

- 首次配置必须提供 API Key；已有密钥时可留空，只修改模型。
- 配置仅写入被 Git 忽略的本机 `.env`。
- 保存后立即重建问答、作业和复习生成服务，无需手动重启。
- 当前问题和最多三个检索片段可能发送给外部模型；使用 `store=False`。

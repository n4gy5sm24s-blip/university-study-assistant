# Task 005：可配置的生成模型

> 状态：已完成

## Goal

在已有检索和引用契约上接入可选的生成模型，把相关原文组织成清楚的中文讲解，同时在未配置或调用失败时保留本地降级能力。

## Scope

### Touch

- AnswerGenerator 接口；
- OpenAI Responses API 适配器；
- 环境变量配置；
- Grounded Answer 的生成与降级策略；
- 使用替身生成器的自动测试。

### Do Not Touch

- 在仓库保存真实 API 密钥；
- 模型自动选择；
- 对话记忆、工具调用和多 Agent；
- Embedding 与向量数据库。

## Acceptance Criteria

1. 配置 `OPENAI_API_KEY` 和 `OPENAI_MODEL` 后可启用 Responses API。
2. 只向模型发送当前问题和最多三个已检索片段。
3. 提示要求模型只基于资料作答并使用 `[n]` 引用。
4. 未配置模型时继续返回 extractive answer。
5. 模型调用失败时安全降级，不丢失检索结果和引用。
6. 自动测试不依赖网络或真实密钥。

## Verification

- 20 项单元测试通过，包括生成成功和调用失败降级；
- 未配置密钥时的完整集成检查通过；
- 官方 OpenAI Python SDK `2.54.0` 可导入并成功建立适配器；
- 未使用真实密钥发起外部模型请求。

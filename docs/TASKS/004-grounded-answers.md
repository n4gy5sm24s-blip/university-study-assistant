# Task 004：基于资料的问答与引用

> 状态：已完成

## Goal

让用户用自然问题查询指定课程，并得到明确区分“有资料依据”和“资料不足”的回答及结构化引用。

## Scope

### Touch

- 自然问题的关键词召回；
- Grounded Answer 服务；
- 文件、章节、片段级引用；
- 无依据时的明确响应；
- 提问 API 和最小界面；
- 自动测试和端到端检查。

### Do Not Touch

- 外部 LLM 服务和密钥；
- 向量数据库和 Embedding；
- 对话记忆；
- 作业与复习工作流。

## Acceptance Criteria

1. “什么是机会成本？”这类自然问题可以召回包含“机会成本”的资料。
2. 有依据时返回原文整理结果以及结构化 citations。
3. citation 包含 document、filename、section、sequence 和 excerpt。
4. 无依据时返回 `no_evidence`，不生成虚构答案和引用。
5. 问答结果严格限定在指定课程。
6. 页面能够显示回答状态和来源。

## Design Note

本任务使用可验证的 extractive answer 完成问答闭环，不冒充已经调用 LLM。后续接入生成模型时，保留相同的检索、引用和无依据契约。

## Verification

- 完整单元测试覆盖自然问题、有依据、无依据和课程隔离；
- 集成检查覆盖上传、检索、问答、引用与删除；
- 全部测试内容均为自制文本。

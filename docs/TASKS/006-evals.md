# Task 006：固定评估集与质量门槛

> 状态：已完成

## Goal

使用完全自制的课程资料和固定问题，重复衡量检索召回、拒答和引用正确性，防止后续修改悄悄降低质量。

## Scope

### Touch

- 两份自制管理学资料；
- 20 个固定评估问题；
- Grounded recall、refusal accuracy、citation accuracy；
- 可重复运行的命令行评估器；
- 90% 总通过率质量门槛。

### Do Not Touch

- 真实教材或用户资料；
- 真实模型调用和主观语言质量评分；
- 在线评估服务；
- 作业和复习工作流。

## Acceptance Criteria

1. 固定评估集不少于 20 个问题。
2. 同时覆盖有依据问题和无依据问题。
3. 有依据问题检查 grounding status、章节和关键词。
4. 无依据问题检查 `no_evidence` 且 citations 为空。
5. 命令返回非零状态表示总通过率低于 90%。
6. 评估不依赖网络、真实密钥或版权教材。

## Verification

- 20 个固定问题全部通过；
- grounded recall：100%；
- refusal accuracy：100%；
- citation accuracy：100%；
- 完整单元测试共 22 项，全部通过。

当前结果只代表自制基准集，不代表真实课程资料的普遍准确率，也不评价生成回答的语言质量。

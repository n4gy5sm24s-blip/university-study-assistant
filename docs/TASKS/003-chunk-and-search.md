# Task 003：文本切分与课程内检索

## Goal

把 ready 状态的资料切分成可定位片段，并允许用户在指定课程内检索相关内容。

## Scope

### Touch

- Chunk 数据模型；
- Markdown 标题感知的切分；
- 纯文本段落切分；
- SQLite FTS5 关键词检索；
- 检索 API 和最小搜索界面；
- 自制资料和自动测试。

### Do Not Touch

- Embedding 和向量数据库；
- LLM 回答；
- PDF 和 OCR；
- 多用户系统。

## Acceptance Criteria

1. 上传资料后自动生成带来源信息的 chunks。
2. 每个 chunk 保留 document_id、章节标题和顺序。
3. 用户可以在一个课程内搜索。
4. 结果返回相关片段、文件名、章节和排序分数。
5. 不同课程的结果严格隔离。
6. 删除资料后对应 chunks 不再出现。
7. 测试覆盖检索命中、无结果、课程隔离和删除。

## Verification

- 运行完整单元测试；
- 运行课程—资料—切分—搜索—删除集成检查；
- 确认测试资料全部为自制内容。

# Task 003：文本切分与课程内检索

> 状态：已完成

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

## Implementation Notes

- Markdown 按标题识别章节，TXT 按段落切分，相邻短段落会合并到最多 800 字符的片段。
- Chunk 保存 `document_id`、`course_id`、章节标题、文档内顺序和正文。
- SQLite FTS5 使用 trigram tokenizer，支持中文连续文本的关键词检索。
- 搜索限定在指定课程，返回文件名、章节、片段顺序和 BM25 排序分数。
- Chunk 的 FTS 写入与删除由数据库触发器同步；上传、切分和索引在同一事务内完成。

# ARCH：大学生学习助手

> 状态：MVP Architecture v1

## 一、架构目标

建立一个“资料可插拔”的学习平台。系统功能不依赖指定教材；用户上传资料后，系统才为对应课程建立知识库。

## 二、产品形态

- Base profile：course-centered learning workspace。
- Capability modules：document ingestion、RAG、learning state、tutor workflow、evaluation。
- MVP 运行方式：本地 Web 应用。
- 推荐技术方案：Python、FastAPI、SQLite、简单 Web UI。
- 模型和 Embedding：通过统一接口接入，避免绑定单一供应商。

## 三、最小端到端流程

    创建课程空间
    → 上传资料
    → 解析文字和页码
    → 切分并建立索引
    → 用户选择学习模式并提问
    → 检索相关片段
    → LLM 生成回答
    → 展示引用
    → 保存反馈和学习状态

## 四、模块边界

| 模块 | 负责 | 拥有的数据 | 不负责 |
| --- | --- | --- | --- |
| Course Workspace | 课程创建、删除和资料归属 | 课程元数据 | 文档解析、模型回答 |
| Document Ingestion | 文件校验、解析、切分 | 原始文件元数据、chunks | 问答策略 |
| Retrieval | 索引和相关片段检索 | 检索索引 | 最终答案 |
| Tutor Orchestrator | 模式选择、Context 组装、工具调用 | 会话状态 | 永久保存原始教材 |
| Learning State | 错题、薄弱点、复习进度 | 用户学习记录 | 教材解析 |
| Evaluation | 测试集、指标和回归结果 | Eval runs | 修改生产数据 |
| UI/API | 用户操作和结果展示 | 临时请求状态 | 绕过业务规则直接访问存储 |

## 五、核心数据实体

- User：MVP 可先使用单一本地用户，保留未来账户扩展接口。
- Course：课程名称、描述、创建时间。
- SourceDocument：文件名、格式、哈希、课程、处理状态。
- Chunk：文本、章节、页码、来源文档、顺序。
- Conversation：课程、模式、消息。
- Citation：回答与 Chunk 的对应关系。
- LearningRecord：知识点、掌握程度、错题和更新时间。
- EvalCase / EvalRun：测试输入、预期行为和实际结果。

## 六、关键接口

- create_course / delete_course
- upload_document / get_ingestion_status / delete_document
- search_chunks
- ask_with_citations
- submit_answer_for_feedback
- create_review_plan
- record_learning_event
- run_eval_suite

接口的具体请求与响应格式在实际实现前写入 docs/CONTRACTS。

## 七、Context Stack

每次模型调用只组装当前任务需要的内容：

1. System Rules：学习诚信、引用和拒答规则；
2. Mode Instruction：教材问答、作业辅导、复习或自由答疑；
3. Course Context：课程名称、教师范围和允许的 AI 使用方式；
4. Retrieved Chunks：相关资料片段和来源；
5. Learning State：必要的薄弱点或进度；
6. Conversation State：当前对话中仍然相关的内容；
7. Tool Results：检索、评分或计划工具返回值。

## 八、失败处理

- 不支持的格式：拒绝导入并说明支持格式。
- 解析失败：保留失败状态，不进入知识库。
- 检索无结果：明确说明资料中未找到。
- 引用缺失：不得把回答标记为“基于资料”。
- 模型不可用：保留问题，返回可理解的错误。
- 删除课程：同时删除资料、索引、对话和学习记录。

## 九、隐私和安全

- MVP 默认本地存储。
- 不在日志中记录完整教材内容、用户答案或密钥。
- 用户资料不用于其他用户的回答。
- 删除操作需要确认并产生可验证结果。
- 外部模型调用前明确哪些文本会离开本机。
- 生成模型默认关闭；启用后只发送当前问题和最多三个检索片段，并使用 `store=False`。

## 十、演进路线

1. 本地单用户、Markdown/TXT/PDF 文本资料；
2. 带引用的 RAG 问答；
3. 作业辅导和答案反馈；
4. 错题与紧急复习；
5. OCR 和更多文件格式；
6. 多用户账户、权限隔离和部署。

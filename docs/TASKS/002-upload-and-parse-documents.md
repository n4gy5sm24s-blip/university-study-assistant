# Task 002：上传并解析课程资料

> 状态：完成

## Goal

用户能够向指定课程上传 Markdown 或纯文本资料，系统完成格式校验、文字提取和处理状态记录。

## Source Context

- docs/SPEC.md
- docs/ARCH.md
- docs/RULES.md
- AGENTS.md
- docs/TASKS/001-bootstrap-course-workspace.md

## Scope

### Touch

- SourceDocument 数据模型；
- 上传、列表和删除资料的 API；
- Markdown 和纯文本解析；
- 文件大小与格式校验；
- 课程页面中的上传界面；
- 自制测试资料与自动测试。

### Do Not Touch

- PDF；
- OCR；
- Embedding 和向量数据库；
- LLM 问答；
- 用户账户和云存储。

## Requirements

- 上传资料必须归属于一个现有课程。
- 只接受 UTF-8 Markdown 和纯文本。
- 原始文件保存在课程隔离目录。
- 记录文件名、类型、大小、哈希、状态和创建时间。
- 删除资料时同时删除原始文件和解析文本。
- 测试只使用自制文本，不使用真实教材。

## Acceptance Criteria

1. 用户可以向课程上传 txt 或 md 文件。
2. 上传后能够查看文件名和 ready 状态。
3. 不支持的格式、空文件和不存在课程会返回清楚错误。
4. 同一课程内重复上传相同内容会被识别。
5. 删除资料后数据库记录和文件都消失。
6. 自动测试覆盖成功和主要失败路径。

## Verification

- 运行单元测试；
- 启动服务；
- 创建课程；
- 上传自制资料；
- 查看资料列表；
- 删除资料并确认文件消失。

## Governance Drift Check

- 如果 SourceDocument 字段变化，更新 ARCH。
- 不引入模型调用或外部存储。
- 不改变学习诚信和资料权属规则。

## Risks

- MVP 只处理 UTF-8 文本，不能直接读取扫描教材。
- 后续添加 PDF 时需要保留页码和章节结构。

## Completion Evidence

- 支持 Markdown 和 TXT 内容上传、列表与删除。
- 实现课程隔离目录、SHA-256 重复检测、2 MB 限制和 ready 状态。
- 错误路径覆盖空文件、不支持格式、重复资料和不存在课程。
- 9 项单元测试全部通过。
- 课程与资料生命周期集成检查通过。
- 测试只使用自制虚构资料。

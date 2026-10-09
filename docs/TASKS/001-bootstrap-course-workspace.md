# Task 001：建立本地应用骨架和课程空间

> 状态：完成

## Goal

建立一个可运行的本地 Web 应用，用户能够创建、查看和删除课程空间。

## Source Context

- docs/SPEC.md
- docs/ARCH.md
- docs/RULES.md
- AGENTS.md

## Scope

### Touch

- 应用启动配置；
- Course 数据模型；
- 创建、列表和删除课程的 API；
- 最小操作界面；
- SQLite 本地数据库；
- 对应自动测试；
- 自制演示数据。

### Do Not Touch

- 文档上传与解析；
- RAG、Embedding 和 LLM；
- 作业辅导；
- 复习计划；
- 用户登录和云部署。

## Requirements

- 使用 Python 和 FastAPI。
- 使用 SQLite 保存课程。
- 课程至少包含 id、name、description 和 created_at。
- 删除不存在的课程返回清楚错误。
- 仓库不得包含真实教材、API Key 或个人资料。

## Acceptance Criteria

1. 一条命令可以启动应用。
2. 用户可以创建课程。
3. 用户可以看到课程列表。
4. 用户可以删除课程。
5. 重启应用后课程仍然存在。
6. 自动测试覆盖创建、列表、删除和不存在错误。

## Verification

- 安装依赖；
- 运行测试套件；
- 启动本地服务并进行一次创建—查看—删除流程。

具体命令在项目骨架建立后写入 README，并以实际运行结果为准。

## Governance Drift Check

- 不修改 SPEC 的产品范围。
- 不加入身份系统或模型调用。
- 如果 Course 数据模型改变，更新 ARCH。

## Risks

- 第一项任务只建立课程容器，还不能读取或回答资料。
- 后续增加多用户时，需要重新设计课程所有权和权限。

## Handoff Notes

- 审查者应重点检查删除行为、SQLite 持久化和任务范围。
- 完成后下一项任务是文档上传、格式校验和解析状态。

## Completion Evidence

- 单元测试：4 项通过，覆盖创建、列表、删除、空名称和不存在错误。
- 冒烟测试：本地服务健康检查、创建、列表和删除 API 全部通过。
- 实际实现：FastAPI、SQLite、本地 Web UI。
- 未加入任务范围外的资料解析、RAG、模型调用或账户系统。

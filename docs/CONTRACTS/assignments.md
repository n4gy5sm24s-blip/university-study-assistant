# Assignment Projects API

## `GET /api/courses/{course_id}/assignments`

返回当前课程的作业项目，按最近更新时间倒序排列。

## `POST /api/courses/{course_id}/assignments`

请求包含 `title`、`prompt`、`draft` 和 `citations`。创建后的 `final_text` 默认等于 `draft`，状态为 `draft`。

## `PATCH /api/courses/{course_id}/assignments/{assignment_id}`

请求包含 `final_text` 和 `status`。`status` 只允许 `draft` 或 `complete`。

删除课程时，所属作业项目通过数据库外键级联删除。

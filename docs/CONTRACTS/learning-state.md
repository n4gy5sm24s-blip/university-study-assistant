# Learning State API

## 自动记录

一次随时问答在找到课程依据后，系统按主引用的 `document_id + sequence` 自动新增或更新学习记录，并累计提问次数。无依据的问题不记录。

## `GET /api/courses/{course_id}/learning`

返回 `total`、`mastered`、`review`、`learning` 计数，以及最近最多 12 个知识点。记录不跨课程。

## `PATCH /api/courses/{course_id}/learning/{record_id}`

请求：`{"status": "mastered"}` 或 `{"status": "review"}`。也允许恢复为 `learning`。

删除资料时级联删除源自该资料的学习记录；删除课程时删除该课程全部学习记录。

## 考前急救联动

- 创建复习计划时，`review` 状态的主题自动优先。
- 闭卷回答经课程资料纠错后返回 `mastered`、`developing` 或 `review`。
- 三种判断分别写回 `mastered`、`learning`、`review`；`review` 主题在当前复习轮次末尾追加一次再测。

# Course Preferences API

## `GET /api/courses/{course_id}/preferences`

读取当前课程的长期写作规则。没有保存过时返回默认中文规则。

## `PUT /api/courses/{course_id}/preferences`

保存 `language`、`citation_style`、`tone`、`target_length` 和 `teacher_requirements`。这些字段会在后续作业生成时加入任务指令。

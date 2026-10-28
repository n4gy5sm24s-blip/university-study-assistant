# Task 024：Railway 部署准备

## 目标

把当前单用户 FastAPI 应用整理成 Railway 可以从 GitHub 构建和启动的私有演示版本，同时避免线上访问者通过公开接口改写 OpenAI API Key。

## 范围

- 增加 Railway 构建、启动和健康检查配置；
- 在 Railway Volume 存在时，把 SQLite 和上传资料写入持久化目录；
- Railway 环境默认禁止通过网页修改模型配置；
- 补充环境变量和部署说明；
- 增加部署配置相关自动测试。

## 不在本任务中

- 不创建 Railway 账户或产生付费订阅；
- 不直接发布公开网址；
- 不实现多用户账户和数据隔离；
- 不迁移到 PostgreSQL 或对象存储；
- 不修改 Chrome Companion 的线上地址。

## 验收标准

1. Railway 能执行 `pip install -r requirements.txt` 并以 `$PORT` 启动 FastAPI；
2. `/api/health` 可作为健康检查；
3. 设置 `RAILWAY_VOLUME_MOUNT_PATH` 后，数据库位于该目录；
4. Railway 环境默认拒绝 `PUT /api/model`；
5. 本地环境仍可显式启用模型配置写入；
6. README 清楚说明尚未解决的认证和多用户风险。

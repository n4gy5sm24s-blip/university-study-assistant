# Task 029：Electron Windows 桌面版

## 目标

把现有本地 Web 作业机封装成可安装的 Windows 桌面应用，用户无需手动启动终端。

## 范围

- Electron 创建原生窗口并自动启动 FastAPI 后端；
- 应用携带官方 Python Embedded Runtime、后端源码和 Web 资源，避免依赖用户安装 Python；
- electron-builder 生成 Windows 便携版压缩包；
- 数据库、上传资料和模型配置保存在 Windows 用户数据目录；
- 关闭桌面应用时关闭其后端进程。

## 不在范围

- 自动更新；
- 代码签名；
- macOS 和 Linux 安装包；
- 改变现有 API 或产品功能。

## 验收

1. 解压便携版后可以直接双击 `Coursework AI.exe`；
2. 双击应用后自动打开作业机，不要求用户启动终端或安装 Python；
3. 创建课程后重启应用，课程仍然存在；
4. 关闭应用后，不留下由应用启动的后端进程；
5. API Key 不进入安装包或 Git。

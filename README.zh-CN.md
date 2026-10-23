# User Behavior Personalization

[English](README.md) · [中文](README.zh-CN.md) · **v0.2.0**

明确偏好保存一次，变化时及时纠正，在下一次任务前读取适用版本。Python 适配器提供绑定用户的档案、事务式纠正、暂停/导出/遗忘控制，以及在启动 Codex、Cursor 前读取档案的包装入口。

![偏好档案流程](docs/images/workflow-v0.2.0.svg)

每条规则保留来源、适用范围、版本和可选有效期。已遗忘来源不能通过重放恢复删除规则。不同用户使用不同记录；用户标识来自本地宿主配置，不能由模型工具参数切换。

下载 [v0.2.0](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.2.0)，使用 Python 3.11+，按[中文教程](docs/tutorial.zh-CN.md)配置。保存档案无需训练模型或托管账号；调用 CLI 模型仍需宿主自己的权限。

真实 Codex 回合已在启动前加载偏好、调用工具并按偏好输出。Cursor 已发现全部档案工具，但模型回合受本机登录与额度限制。自动聊天账号映射、每日反思调度、会话历史采集以及已运行桌面聊天的逐轮钩子均未内置；需要保证新 CLI 调用前加载档案时，应使用包装入口。

[Apache-2.0](LICENSE) · [隐私控制](docs/privacy-and-memory-control.md) · [KarmenLoop](https://karmenloop.com)

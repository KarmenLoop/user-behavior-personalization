# User Behavior Personalization · 用户偏好记录

[English](README.md) | 简体中文

把有用偏好写进用户能检查和更正的资料中。这个技能规定如何将明确反馈整理为有范围的使用指导，避免把猜测悄悄记成个人事实。

[下载 v0.1.1](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.1.1) · [教程](docs/tutorial.zh-CN.md) · [反馈问题](https://github.com/KarmenLoop/user-behavior-personalization/issues)

## 用途与范围

包内是技能说明、空白模板和合成样例。身份核实、私有存储、加载、删除导出，以及调度和同步均由宿主提供。

![用户偏好记录流程示意](docs/images/workflow-v0.1.1.svg)

*v0.1.1 的流程示意，非应用截图或运行验收。*

## 开始使用

解压 ZIP，在顶层目录运行 python3 scripts/install_skill.py --destination ../installed-skills/user-behavior-personalization。目标必须是源目录外的新目录，再通过宿主支持的加载方式选择它。

由宿主明确 PROFILE_ROOT、USER_ID、USER_TIMEZONE、MEMORY_ENABLED、CONVERSATION_SOURCE、REFLECTION_TRIGGER。这些是集成约定字段，不是附带程序会读取的环境变量。使用私有用户目录里的空白模板开始。

## 第一次有用的任务

使用含明确更正的合成对话，让宿主提出对应范围的偏好并展示来源，只通过现有且已授权的操作保存，再从已保存记录验证后续读取。

检查一次冲突更正，再通过真实宿主测试导出或删除。仓库检查确保模板空白及包内容规范，不代表已通过真实用户或跨设备全链路认证。

## 常见问题

**装好后会记住所有对话吗？** 不会。宿主必须明确提供已授权的对话、存储和加载。本包不会启动服务或注册定时器。

## 文档与许可证

[下载到实践的使用指南](docs/tutorial.zh-CN.md) · [LICENSE](LICENSE)

Apache-2.0. 许可证条件以原文为准，再分发时保留包内法律文件。 [KarmenLoop](https://karmenloop.com).

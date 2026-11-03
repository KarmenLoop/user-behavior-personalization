# 快速开始 — v0.7.0

[English](quickstart.md) · [中文](quickstart.zh-CN.md)

下载并校验 [v0.7.0](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.7.0)，解压后在包目录中使用 Python 3.11 或更新版本。

```sh
python3 -B scripts/check_package.py
python3 -B scripts/workspace.py --root ../private-profile --subject demo --enable-conversations
```

打开终端显示的本地地址。点击「体验一个合成示例」，查看三个会话的证据，然后确认简短回答的习惯。进入「用于下一次任务」预览效果，再将回答长度改为「仅用于这次任务」的详细模式。原来的长期偏好不会改变。

保存方案后，可以评价这次提示方案是否有帮助。整个本地流程不需要模型账号；预览展示的是实际拼接的提示内容，不是模型生成的回答。完成后在终端按 Ctrl+C 停止服务。

继续阅读[完整教程](tutorial.zh-CN.md)、[指定文件自动导入](automatic-learning.zh-CN.md)或 [Codex/Cursor 接入](host-integration.zh-CN.md)。私有数据目录应放在 Git 之外。[验收记录](evaluation.zh-CN.md)列出了学习能力与真实模型调用目前的边界。

# 快速开始 — v0.4.0

[English](quickstart.md) · [中文](quickstart.zh-CN.md)

下载并核对 [v0.4.0](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.4.0)，解压后在包内使用 Python 3.11+：

```sh
python3 -B scripts/check_package.py
python3 -B scripts/learn_conversation.py --root ../private-profile --subject demo --enable-conversations --input examples/conversations/sample.zh-CN.json
python3 -B scripts/demo_conversations.py --root ../new-conversation-demo
```

导入器打印实际自由文本提案与表达观察，不替用户确认。生命周期演示使用新的目录与合成对话，通过真实本地进程执行审查、预测、模型提案暂存、删除和重置，不调用模型提供方。

自己的 JSON/JSONL、独立场景、Codex/Cursor 配置、细粒度删除和真实宿主验收见[教程](tutorial.zh-CN.md)。实验性预测目前英文改写覆盖较弱，使用前先看[验收结果](evaluation.zh-CN.md)。

原有[结构化反馈流程](structured-feedback.zh-CN.md)继续可用，需独立的 `--enable-observations`。私有存储放在 Git 外。

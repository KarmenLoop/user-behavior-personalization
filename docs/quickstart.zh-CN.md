# 快速开始 — v0.3.0

[English](quickstart.md) · [中文](quickstart.zh-CN.md)

下载并解压[当前版本](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.3.0)，使用 Python 3.11+，在解压目录运行：

```sh
python3 -B scripts/check_package.py
python3 -B scripts/demo_learning.py --root ../new-personalization-demo
```

第二条命令使用新的私有目录和合成输入，实际执行本地学习、审查与删除流程，不调用模型。查看输出检查与目录；练习结束后档案暂停、内容清空，仅保留最小防重放标记。

随后按[完整教程](tutorial.zh-CN.md)绑定本人 subject，选择允许记录的反馈，配置 Codex 或 Cursor，并测试真实模型回复。存储目录放在 Git 外。观察需要 `--enable-observations`；只保存明确规则时无需开启。

原有 [Markdown 档案格式](../references/profile-format.md)与[反思协议](../references/reflection-workflow.md)保留，供自行管理文件的宿主使用。随包适配器使用 SQLite，不会自动调度反思、采集历史或维护这些 Markdown 档案。

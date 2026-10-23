# User Behavior Personalization v0.2.0 教程

[English](tutorial.en.md) · [中文](tutorial.zh-CN.md)

## 安装并绑定用户

解压当前版本，使用 Python 3.11+，将私有数据目录放在 Git 之外。由本地账号所有者把目标用户映射为稳定的 `--subject` ID；本版本不自动识别 ChatGPT/Cursor 账号。不要让会话自由选择其他用户，也不要向不可信的本地用户开放共享数据目录。

```sh
python /path/to/scripts/host.py --root /private/profiles --workspace /path/to/project --subject owner --install-host codex install
python /path/to/scripts/host.py --root /private/profiles --workspace /path/to/project --subject owner --install-host cursor install
```

重载并批准特定服务，确认发现五个档案工具。用户标识在服务器配置中绑定，不在工具参数里传递。

## 保存纠正并核对

先使用任务上下文调用 `profile_read`。用返回的当前版本调用 `profile_correct`。规则需要 `id`、`statement`、`scope`（`*` 表示所有上下文）、新 `source_id`、`source_summary` 和 `kind`（`explicit` 或 `correction`）。可选 `expires_at` 必须带时区。仅保存用户授权的偏好；适配器不会从文本推定同意。

在另一宿主用匹配上下文读取，应得到同一规则；无关上下文不返回它，其他绑定用户读取自己的档案。纠正规则时保留 ID、使用真正的新来源 ID 和当前版本。旧版本写入会被拒绝，重复来源会去重。

无需模型也可用 JSON 参数文件调用：`python /path/to/scripts/host.py --root /private/profiles --workspace /path/to/project --subject owner call profile_read --input request.json`。

## 在新任务前加载偏好

将任务写入私有提示文件，运行：

```sh
python /path/to/scripts/run_host.py --root /private/profiles --subject owner --context writing --host codex --workspace /path/to/project --prompt /private/task.txt
```

Cursor CLI 使用 `--host cursor`。每个宿主仍需自己的登录与模型权限。包装入口先读取当前适用偏好，再启动宿主，把使用版本、规则 ID、实际退出码及输出保存到 `host-runs`。它不创建周期任务，也不安装全局生命周期钩子。超时时会终止它所拥有的进程组，重试前需检查外部影响。

## 暂停、导出与遗忘

用当前版本调用 `profile_pause`。暂停时普通读取不返回偏好，纠正需要先恢复；`profile_export` 仍可用。`profile_forget` 移除指定规则及其历史内容、删除适配器控制的导出，仅保留防重放所需来源哈希。外部导出、备份与物理存储残留是独立副本；SQLite 启用 secure-delete，但不承诺 SSD 物理抹除。

不要将私有存储加入发布包。备份前停止写入。读取失败时包装入口会失败，不会声称已应用偏好。

验收使用了真实 Codex 回合并保存收条。Cursor 工具发现已通过，模型回合及 Windows/Linux 原生使用尚未验收。反思定时器、自动历史采集和身份提供方仍需明确的宿主接入，不能只靠说明文档宣称可用。

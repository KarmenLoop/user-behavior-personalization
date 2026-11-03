# 宿主接入 — v0.5.0

[English](host-integration.md) · [中文](host-integration.zh-CN.md)

浏览器工作台、CLI 与 MCP 标准输入输出共用同一本地适配器及 [25 个工具](tools.zh-CN.md)。用户和私有目录在进程启动时固定，工具调用不能切换身份。

## 先使用本地工作台

```sh
python3 -B scripts/workspace.py --root ../private-profile --subject owner --enable-conversations
```

打开终端显示的本地地址，导入选定反馈、审阅习惯、预览任务并记录明确评价。这个流程不发送模型请求。需要连续导入时，在另一终端用相同目录与用户启动[指定文件监听](automatic-learning.zh-CN.md)。它只在运行期间导入该文件，不会安装后台服务或发现其他账号。

## 配置 Codex 或 Cursor

```sh
python3 scripts/host.py --root ../private-profile --subject owner \
  --workspace /path/to/project --enable-conversations --install-host codex install
```

接入 Cursor 时改用 `--install-host cursor`。安装器写入 `.codex/config.toml` 或 `.cursor/mcp.json`，保留已有配置，遇到同名服务器会拒绝覆盖。配置中记录 Python 路径、包路径、私有目录、用户及收集开关。直接记录结构化事件需另外开启 `--enable-observations`。

在宿主中重新加载服务器并查看工具列表，实际核对两个宿主能否读取同一条已确认偏好。配置生成及 MCP 调用成功不等于模型已采用规则；真实回答需单独检查。

宿主的指令机制是另一层配置。Codex 读取有范围的 `AGENTS.md`；Cursor 项目规则使用 `.cursor/rules/*.mdc`。安装本服务器不会重写这些文件，也不会强制每轮调用。参见官方 [Codex 指南](https://developers.openai.com/codex/guides/agents-md)与 [Cursor 规则](https://cursor.com/docs/rules)。

请运行实际安装的 v0.5.0 脚本。旧版技能副本或仍指向旧目录的 MCP 配置，会继续使用旧实现。安装到新目录后，检查并将现有服务器配置改为新路径，再重启工作台或重新加载 MCP。安装器不会静默覆盖已有副本或重复服务器。可以在该安装目录运行 `build_context.py --help` 或 `run_host.py --help` 核对临时覆盖选项。

## 让预览与执行使用同一套选择逻辑

`profile_plan` 展示采用和排除的规则及原因。`scripts/build_context.py` 与 `scripts/run_host.py` 用相同选择器构建实际请求内容。它们都支持场景、临时类型设置、排除规则及偏好文本预算。

```sh
python3 scripts/build_context.py --root ../private-profile --subject owner \
  --context writing --task-file /path/to/private-task.txt \
  --override response_length=detailed --preference-budget 4000
```

JSON 输出包含 `messages` 及本地个性化元数据。由你自己的客户端发送需要的请求字段。构建器不联网、不保存原始任务；重定向后的输出属于你另外管理的私有副本。

`run_host.py` 在一次新的 Codex 或 Cursor CLI 调用前加载偏好，将结果输出到终端。保存的回执只有元数据，没有原始提示或回答。Codex 通过标准输入接收提示；当前 Cursor CLI 路径使用位置参数，同一本地用户的进程检查工具可能看到内容。账号、模型权限、终端日志及提供商留存仍由相应系统管理。它不会给已经运行的桌面聊天安装自动钩子。

## 可选的模型辅助学习

`profile_model_context(context)` 返回有限的已存摘录和提议格式。经授权的宿主可将其发送给选定模型，包括兼容 DeepSeek 风格的聊天 API。返回结果通过 `profile_model_propose` 提交，工具会核对已知来源、精确引用、类别与范围。通过校验的提议仍需用户审阅。

DeepSeek JSON Output 约束格式，不证明内容真实。需要拒绝空白或截断结果、校验字段及来源白名单，并将摘录视为数据而非指令。参见[官方 JSON Output 指南](https://api-docs.deepseek.com/guides/json_mode/)。本包不包含提供商凭据或模型循环，也未声称完成 DeepSeek 真实调用验收。

## 明确接入边界

宿主负责可信身份、获准使用的消息、准确的角色与来源标识，以及用户真实的审阅决定。来源字符串是宿主记录，并非独立的授权证明。当前指令与普通执行权限仍然有效。

每日调度、账号历史导出、操作系统隔离、多设备同步及外部留存需要宿主分别实现。[早期反思契约](../references/reflection-workflow.md)说明了这些责任。指定文件监听是已实现的前台导入器，不代表整套后台服务已具备。本地与提供商结果见[当前验收记录](evaluation.zh-CN.md)。

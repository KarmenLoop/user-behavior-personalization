# 用户行为个性化 v0.7.0 结构化反馈教程

[English](structured-feedback.en.md) · [中文](structured-feedback.zh-CN.md)

先完成下面的本地练习：它只使用合成反馈，无需模型账号。随后接入一个宿主，检查真实回复，再决定是否用于日常工作。

## 1. 下载并检查

从 [v0.5.1](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.7.0) 下载 ZIP 和 `SHA256SUMS.txt`。解压前核对压缩包 SHA-256：macOS 使用 `shasum -a 256`，Linux 使用 `sha256sum`，PowerShell 使用 `Get-FileHash -Algorithm SHA256`。

需要 Python 3.11 或更新版本，适配器没有第三方 Python 依赖。在解压目录打开终端：

```sh
python3 --version
python3 -B scripts/check_package.py
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_publication.py
```

Windows 可按实际安装使用 `py -3.12` 代替 `python3`。安装、工具调用和 MCP 配置应使用同一解释器。这些检查验证本地代码与发布一致性，不会调用模型。

需要可携带副本时，将整个包安装到新的宿主目录：

```sh
python3 scripts/install_skill.py --destination ../installed-skills/user-behavior-personalization
```

目标目录必须不存在；`SKILL.md`、`scripts/`、`references/` 和 `assets/` 要保持在一起。私有用户档案不要放进公开仓库。

## 2. 走完一次真实的本地学习流程

需要单命令版本时，运行同类合成练习：

```sh
python3 -B scripts/demo_learning.py --root ../new-synthetic-demo
```

选择尚不存在的目录。它启动真实本地 CLI 进程，不是模型效果测试。


下面是完整的 Python 练习，可保存到包外运行，也可在工作目录为解压包时粘贴到 Python。它每次写入前都读取当前版本，不靠猜测 revision。

```python
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile

# Run from the extracted package. This store contains synthetic data only.
package = Path.cwd()
private = Path(tempfile.mkdtemp(prefix="personalization-demo-"))
command = [sys.executable, "-B", str(package / "scripts/host.py"),
           "--root", str(private), "--subject", "demo",
           "--enable-observations"]

def call(tool, arguments):
    result = subprocess.run(command + ["call", tool],
                            input=json.dumps(arguments), text=True,
                            capture_output=True, check=True)
    return json.loads(result.stdout)

def revision():
    return call("profile_read", {"context": "code-review"})["revision"]

# Explicit requests do not need three observations.
call("profile_correct", {"expected_revision": revision(), "rule": {
    "id": "status-length", "statement": "Keep status updates concise.",
    "scope": "status-update", "source_id": "demo-explicit-1",
    "source_summary": "Synthetic user asked for concise status updates.",
    "kind": "explicit", "dimension": "response_length", "value": "concise"
}})
assert call("profile_read", {"context": "code-review"})["rules"] == []

# Three distinct sessions, not three copies of one message.
for day in (3, 2, 1):
    occurred = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=day)
    call("profile_observe", {"expected_revision": revision(), "event": {
        "id": f"demo-event-{day}", "source_id": f"demo-feedback-{day}",
        "session_id": f"demo-session-{day}", "context": "code-review",
        "dimension": "structure", "value": "conclusion_first",
        "signal": "positive", "occurred_at": occurred.isoformat()
    }})

insights = call("profile_insights", {"context": "code-review"})
print(json.dumps(insights, indent=2))
candidate = next(c for c in insights["candidates"]
                 if c["status"] == "ready_to_review")
assert call("profile_read", {"context": "code-review"})["rules"] == []

# Synthetic confirmation for this exercise only.
# A real integration must ask the user and use the actual review source.
accepted = call("profile_review", {
    "expected_revision": revision(), "candidate_id": candidate["candidate_id"],
    "decision": "accept", "source_id": "demo-user-confirmation-1"
})
assert call("profile_read", {"context": "code-review"})["rules"]

call("profile_pause", {"expected_revision": revision(), "paused": True})
assert call("profile_read", {"context": "code-review"})["rules"] == []
export = call("profile_export", {})
print("Private export:", export["path"])

# Deletion remains available while paused.
call("profile_forget", {"expected_revision": revision(),
                        "rule_id": accepted["rule_id"]})
call("profile_reset", {"expected_revision": revision()})
assert call("profile_read", {"context": "code-review"})["paused"] is True
print("Demo complete. Private demo directory:", private)
```

预期结果：明确偏好立即保存；三个独立会话的反馈产生待确认候选；确认前，该场景的普通检索仍为空；暂停会关闭普通检索，但仍能导出和删除；重置后保持暂停。程序会输出合成档案所在目录，便于检查或删除。

新的 `source_id` 必须对应真实的新陈述或反馈，不能换个 ID 绕过遗忘限制。来源和会话编号由宿主提供，并不是“三次独立互动确实发生过”的密码学证明。

## 3. 选择维度和场景

| 维度 | 可用值 | 场景示例 |
|---|---|---|
| `response_length` | `concise`、`balanced`、`detailed` | `status-update` |
| `structure` | `conclusion_first`、`steps`、`examples`、`code_first`、`bullets` | `code-review` |
| `teaching` | `explain_back`、`worked_example`、`practice` | `learn-python` |
| `initiative` | `ask_first`、`suggest_next` | `project-planning` |
| `workflow_next_step` | `clarify`、`plan`、`implement`、`test`、`review`、`summarize` | `after-implementation` |
| `language` | `en`、`zh` | `technical-explanation` |

场景名应稳定、具体。匹配使用完整标签并忽略大小写。明确的全局偏好使用 `scope: "*"`；行为观察应记录反馈发生的具体场景。临时要求默认不形成长期观察；确实要存储临时偏好时，由用户授权，并给明确规则设置带时区的 `expires_at`。

反对反馈使用 `signal: "negative"`，针对用户实际拒绝的维度和值。“这个例子不对”不等于“以后都不要举例”。沉默、助手输出、引用同事的话，以及模型自己推测的用户动机，都不是本人反馈。

## 4. 接入 Codex 或 Cursor

先创建目标项目，把私有数据目录放在 Git 之外。由宿主设置把一个不透明的 subject ID 绑定到正确用户。

```sh
python3 scripts/host.py --root ../private-profile --subject owner \
  --workspace /path/to/project --enable-observations --install-host codex install
python3 scripts/host.py --root ../private-profile --subject owner \
  --workspace /path/to/project --enable-observations --install-host cursor install
```

只需要明确偏好时，省略 `--enable-observations`。这是服务启动配置，工具参数不能自行授予观察权限。安装助手保留已有条目；提示服务已存在时，请检查后明确修改，不要重复添加。

重载宿主，批准这个服务，检查 `tools/list`，再调用 `profile_read`。确认 subject 和数据根正确，保存一个合成偏好，并从第二个宿主读取。同用一个目录不会自动关联线上账号。

随后让每个宿主回答一个无害问题，设置容易判断的风格偏好，核对规则是否被加载、真实回复是否遵守，以及纠正后是否变化。配置成功、MCP 可调用、模型确实生效，是三个不同的验收步骤。

## 5. 在新的 CLI 任务前加载偏好

准备一个私有任务文件，运行：

```sh
python3 scripts/run_host.py --root ../private-profile --subject owner \
  --context code-review --host codex --workspace /path/to/project \
  --prompt /path/to/private-task.txt
```

Cursor CLI 使用 `--host cursor`。包装入口先加载已确认规则，再启动宿主；输出流向终端，本地只保存绑定用户的元数据收条，不保存原始提示或模型输出文件。终端历史、宿主日志及提供方留存不属于这个存储目录的控制范围。包装入口不会建立定时任务，也不会为已经打开的聊天补装逐轮钩子。

## 6. 生成模型 API 请求内容

```sh
python3 scripts/build_context.py --root ../private-profile --subject owner \
  --context code-review --task-file /path/to/private-task.txt
```

命令输出包含 `messages` 和本地 `personalization` 元数据。自行编写的 DeepSeek 类聊天客户端，可把 **`messages` 的值**放进请求；不能把整个输出当作提供方的完整请求格式发送。此命令不会联网，也不需要 API 密钥。若重定向到文件，该文件包含任务和已选偏好，应按私有数据保管并单独清理。

DeepSeek 聊天 API 是模型接口，不是直接的 MCP 客户端。需要工具调用时，宿主必须自行实现工具白名单、版本校验、返回验证和用户授权，参见[宿主接入](host-integration.zh-CN.md)。

## 7. 查看、更正、遗忘和重置

- `profile_insights` 展示候选依据；支持度是工程规则，不是心理判断的确定性。
- `profile_correct` 使用原规则 ID 和新来源更正明确偏好；需要结构化冲突处理时，同时提供 `dimension` 与 `value`。
- `profile_review` 的 `decision: "reject"` 拒绝本次候选。未来新证据可能值得重新审查；拒绝不会被当成同意。
- `profile_forget_observations` 使用非空 `observation_ids` 列表，删除指定观察和依赖它们的规则。
- `profile_forget` 删除规则及关联证据。已经复制出去的导出与提供方历史需另行处理。
- `profile_reset` 清空内容并暂停档案。它保留最小来源哈希来抑制重放，不承诺物理擦盘。

所有写操作都需要当前 `expected_revision`。遇到过期版本，不要盲目重试；先读取变化，再判断原来的更改是否仍然合适。

## 8. 排错与进阶验收

| 现象 | 检查方向 |
|---|---|
| `STALE_REVISION` | 另一笔写入改变了档案，重新读取再决定。 |
| 观察未开启 | 获授权后以 `--enable-observations` 启动服务，不能从聊天内容自行推定授权。 |
| `MEMORY_PAUSED` | 仅按用户要求恢复；查看和删除仍然可用。 |
| 来源已遗忘 | 不要替换 ID 重放旧来源；需要时取得真正的新反馈。 |
| 没有可确认候选 | 检查独立会话、场景、时效、反对证据与已有明确偏好。 |
| 升级后某场景不再匹配 | 当前版本使用完整标签，`art` 不再匹配 `cartography`。 |
| 观察条数到上限 | 审查并删除不再需要的证据；系统不会静默清理。 |
| 宿主忽略已存偏好 | 检查实际工具加载或使用包装入口；保存成功不等于模型遵守。 |

进阶使用时，对比不同场景、尝试更改偏好、加入真实反对证据，并检查删除后能否防止重新出现。按[验收指南](evaluation.zh-CN.md)保留结果，不要把测试通过数当成“理解用户程度”。

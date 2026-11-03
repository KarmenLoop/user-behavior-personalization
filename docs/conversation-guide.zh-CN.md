# 对话学习教程 — v0.7.0

[English](conversation-guide.en.md) · [中文](conversation-guide.zh-CN.md)

本教程从实际对话文本开始，走完提取、审查、档案使用、历史后续请求检索与来源删除。练习使用合成数据；导入自己的记录时，只选择有权处理的会话。

## 1. 下载和安装

从 [v0.5.1](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.7.0) 下载 ZIP 和 `SHA256SUMS.txt`，解压前核对 SHA-256。macOS 使用 `shasum -a 256`，Linux 使用 `sha256sum`，PowerShell 使用 `Get-FileHash -Algorithm SHA256`。

需要 Python 3.11+，没有第三方 Python 运行依赖。在解压目录运行：

```sh
python3 --version
python3 -B scripts/check_package.py
python3 -B -m unittest discover -s tests -v
```

Windows 可按实际安装使用 `py -3.12`。需要便携副本时，运行 `python3 scripts/install_skill.py --destination ../installed-skills/user-behavior-personalization`，目标目录必须尚不存在。包内文件保持完整，私有数据放在 Git 外。

## 2. 导入选定的对话

```sh
python3 scripts/learn_conversation.py --root ../private-profile --subject demo \
  --enable-conversations --input examples/conversations/sample.zh-CN.json
```

命令读取当前版本，导入指定文件，再输出计数和档案；不会自动确认提案。subject 应由宿主绑定到本人，不是根据聊天昵称推测身份。

JSON 格式如下：

```json
{
  "session_id": "release-planning-1",
  "context": "release-planning",
  "messages": [
    {
      "id": "message-1",
      "role": "user",
      "text": "以后发布方案里，都要加上回滚检查清单。",
      "at": "2026-11-03T00:00:00Z"
    }
  ]
}
```

使用真实时间和稳定来源编号。`session_id` 与消息 `id` 使用 1–80 位 ASCII 字母、数字、连字符或下划线。消息必须按时间排列；每批最多 100 条，每条最多 4,000 字符。角色可为 `user`、`assistant`、`system`、`tool`，只有用户消息成为保留的本人证据。

JSONL 文件每行一个消息对象，命令中另传会话和场景：

```sh
python3 scripts/learn_conversation.py --root ../private-profile --subject owner \
  --enable-conversations --format jsonl --session-id project-session-1 \
  --context release-planning --input /path/to/selected-messages.jsonl
```

追加时，按原顺序提交原会话前缀和新消息。相同内容重复导入会去重；改写已存用户消息、更换场景或重排原历史会被拒绝，避免更新导出时悄悄改变已确认偏好的依据。

## 3. 走完学习与删除流程
也可用一条命令运行合成生命周期：

```sh
python3 -B scripts/demo_conversations.py --root ../new-conversation-demo
```

它执行真实本地进程，包含不调用提供方的模型提案暂存。请选择新的目录。


在包目录运行下面的 Python。每次写入前都读取当前版本，不依赖写死的计数：

```python
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile

# Run from the extracted package. All messages here are synthetic.
private = Path(tempfile.mkdtemp(prefix="conversation-learning-"))
base = [sys.executable, "-B", str(Path.cwd() / "scripts/host.py"),
        "--root", str(private), "--subject", "demo", "--enable-conversations"]
context = "database-release"

def call(tool, arguments):
    result = subprocess.run(base + ["call", tool], input=json.dumps(arguments),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)

def revision():
    return call("profile_read", {"context": context})["revision"]

now = dt.datetime.now(dt.timezone.utc)
query = "Check the database schema migration plan."
followup = "Write a rollback checklist for the database migration."
conversations = []
for session in (1, 2):
    when = now - dt.timedelta(days=3-session)
    text = [query, followup]
    if session == 1:
        text.insert(0, "From now on, include a rollback checklist in release plans.")
    conversation = {
        "session_id": f"release-{session}", "context": context,
        "messages": [{"id": f"message-{i}", "role": "user", "text": body,
                      "at": (when + dt.timedelta(minutes=i)).isoformat()}
                     for i, body in enumerate(text)]
    }
    conversations.append(conversation)
    call("conversation_import", {"expected_revision": revision(),
                                 "conversation": conversation})

portrait = call("profile_portrait", {"context": context})
print(json.dumps(portrait, indent=2))
proposal = next(p for p in portrait["pending_preferences"]
                if p["category"] == "workflow")
assert call("profile_read", {"context": context})["rules"] == []

# Synthetic approval for this exercise; real use needs the user's actual decision.
reviewed = call("profile_proposal_review", {
    "expected_revision": revision(), "proposal_id": proposal["id"],
    "decision": "accept", "source_id": "demo-user-review-1"
})
assert call("profile_read", {"context": context})["rules"]

forecast = call("profile_forecast", {"context": context, "request": query})
print(json.dumps(forecast, indent=2))
assert forecast["status"] == "suggested"
assert forecast["candidates"][0]["suggestion"] == followup

# Forget the source of the confirmed rule and one supporting forecast session.
call("profile_forget_conversation", {"expected_revision": revision(),
                                     "session_id": "release-1"})
assert call("profile_read", {"context": context})["rules"] == []
assert call("profile_forecast", {"context": context,
                                 "request": query})["status"] == "insufficient_evidence"
call("profile_reset", {"expected_revision": revision()})
assert call("profile_read", {"context": context})["paused"] is True
print("Exercise complete. Private synthetic store:", private)
```

这个例子能提出后续建议，是因为两个会话里出现相同的前置请求与后续请求。它证明调用路径可执行，不代表对改写表达的效果。[验收指南](evaluation.zh-CN.md)中的冻结诊断使用独立查询，并保留漏检。

## 4. 查看协作档案

`profile_portrait({"context": "release-planning"})` 返回：

| 字段 | 用途 |
|---|---|
| `confirmed_preferences` | 本人已审查或明确保存的偏好，可进入相应场景的检索。 |
| `pending_preferences` | 沟通、工作流程、目标、约束等提案，附来源原文。 |
| `writing_observations` | 消息和会话数、长度中位数、列表、问句、语言混合与例子。 |

自定义术语、详细发布惯例和本人学习目标，都可以保留为自由文本。提取器寻找中英文明确表达，不要求归入原有六个观察标签。间接表达可能漏掉；没提取到一句话，不代表用户没有这种偏好。

表达统计描述用户在导入消息中怎么写，不会自动要求助手模仿。用户确实希望风格相近时，应一起查看例子，再确认希望助手采用的规则。

## 5. 审查或纠正提案

先读取档案，再调用 `profile_proposal_review`：传当前 `expected_revision`、提案的 `id` 作为 `proposal_id`、真实审查来源 `source_id`，以及 `decision: "accept"` 或 `"reject"`。

需要替换冲突的已确认规则时，加上该规则的 `replace_rule_id`。系统不会自动理解并合并所有自由文本冲突；应核对原规则和提案后再替换，保留不相关偏好。

明确表达可以立即成为提案。三个会话门槛属于原有结构化反馈路径，不用于这里的明确语言提取。继续使用 `profile_observe` 和固定维度时，参见[结构化反馈指南](structured-feedback.zh-CN.md)。

## 6. 查询相近任务之后通常会问什么

向 `profile_forecast` 传入完整场景和当前请求文本。查看 `status`、`candidates`、候选的 `suggestion`，以及包含 `previous_request`、`next_request` 的历史证据。

- `suggested`：领先的历史后续请求获得足够一致支持，可以作为建议提供。
- `insufficient_evidence`：匹配会话太少、证据过旧或支持不足。
- `conflicted`：不同后续走向相互竞争，无法明确建议。

即使不是 `suggested`，返回中也可能有供查看的候选，不应直接包装成已确定预测。算法比较英文词与子词、中文字符模式，考虑时效，每个会话最多贡献一次匹配。返回的是实际保留的历史原话，不是新编的计划，更不会执行那句话。

## 7. 可选：让宿主模型辅助归纳

`profile_model_context` 选取一个场景中最多 20 条近期保留片段，附上提取约定。宿主可以按授权交给自己的模型；本地工具本身不发送。

模型提案通过 `profile_model_propose` 回传，每项包含 `statement`、`scope`、`category` 和 `evidence`，证据要有已存 `source_key` 与精确匹配的 `quote`。适配器检查来源存在、场景、引文、长度和基本不安全内容模式。通过检查代表可追溯，不代表模型已经正确理解用户；仍需 `profile_proposal_review` 记录本人决定。

具体流程与 DeepSeek 边界见[宿主接入](host-integration.zh-CN.md)。不要把 API 密钥或隐藏模型推理存进档案。

## 8. 接入宿主并使用

```sh
python3 scripts/host.py --root ../private-profile --subject owner \
  --workspace /path/to/project --enable-conversations --install-host codex install
```

Cursor 使用 `--install-host cursor`；若同时需要结构化反馈，另加 `--enable-observations`。重载并批准服务，核对 25 个工具，再实际调用。已有条目会保留，遇到重名错误应检查配置，而不是静默新增第二个服务。

确认后的规则可由 `profile_read`、`scripts/run_host.py` 或 `scripts/build_context.py` 加载。包装入口使用 `--context`、`--host`、`--workspace`、`--prompt`；请求生成器使用 `--context` 和 `--task-file`。包装入口输出流向终端，收条只保存元数据。Codex 通过 stdin 接收组合提示；当前 Cursor CLI 路径使用位置参数，同用户进程检查可能看到内容。

## 9. 查看、暂停和删除

`profile_pause` 暂停普通使用与学习，导出、删除仍可用。`profile_forget_conversation` 接收 `session_id`，删除会话消息及依赖它的提案、规则、表达统计贡献和前后请求关系。中间消息被删，不会把它前后的请求拼成新关系。`profile_reset` 清空内容并暂停，保留最小来源哈希抑制重放。

最多存储 80 个会话、400 条用户记录，每条保留清理后的前 600 字符片段及特征、哈希。删除不再需要的证据，不要靠更换来源 ID 绕过容量或遗忘。外部备份、导出、终端输出和提供方历史仍是独立副本，参见[隐私控制](privacy-and-memory-control.zh-CN.md)。


只删除指定消息时，调用 `profile_forget_messages`，传当前版本和从档案或模型上下文取得的非空 `source_keys` 列表。相关提案、规则、表达贡献和序列关系会连带清理，保留同会话的其他消息，缺口两侧不会生成新关系。

档案也比较近 30 天与第 31–90 天的请求长度；每个窗口至少有三个会话才做比较。它描述表达习惯可能的变化，不会自动修改回复偏好。

## 10. 评价实际效果

运行 `python3 -B scripts/evaluate_conversations.py` 查看冻结合成诊断。分别阅读覆盖率、输出条件下的准确率、暂不建议、失败编号和提取漏检。十一条查询的结果是诊断，不是广泛准确性的证明。还应比较接受偏好前后的真实回复，并请用户判断是否帮助完成任务。

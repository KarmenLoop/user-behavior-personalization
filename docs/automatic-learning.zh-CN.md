# 从选定文件自动学习 — v0.7.0

[English](automatic-learning.en.md) · [中文](automatic-learning.zh-CN.md)

来源由你选择。导入器读取新的完整记录，实验性习惯学习器从保留的本人片段中识别受支持的重复反馈；哪些成为长期偏好，仍由你审查。指定文件导入器和任务选择器本身是否可用，与学习器能否识别某种说法，需要分别判断。

## 哪部分会自动完成

前台监听器读取指定文件中新追加的完整行。`conversation_import` 更新现有存储，`profile_habits` 从支持的纠正表达中发现习惯，不需要逐条手动赋予标签。三个独立会话、时效和相反证据共同决定能否建议确认；重复输入和同一会话内的重复不增加独立支持。

当前习惯发现把受支持表达映射到既有协作维度：回答长度、结构、教学、主动程度、下一步流程和语言。它不会从所有句子里学会任意语义概念。自由文本偏好、专用词、目标和约束仍走明确提案路径，可选宿主模型桥接还能暂存其他带来源解释。

## 两种 JSONL 格式用途不同

| 命令 | 每行是什么 |
|---|---|
| `learn_conversation.py --format jsonl` | 一条消息，会话与场景由命令参数提供。 |
| `watch_conversations.py` | 完整会话对象，包含 `session_id`、`context`、`messages`。 |

监听记录写成一行，并以换行符结束：

```json
{"session_id":"writing-1","context":"writing","messages":[{"id":"feedback-1","role":"user","text":"太长了，请简短一点。","at":"2026-11-03T00:00:00Z"}]}
```

真实数据使用真实时间和稳定编号。追加已有会话时，新快照应包含原本有序的全部前缀和新消息；不要改写已经处理过的文件字节，也不要修改已存的用户原话。

## 启动监听

```sh
python3 -B scripts/watch_conversations.py --root ../private-profile --subject owner \
  --input /path/to/selected.jsonl --enable-conversations
```

默认每两秒检查，`--interval` 可设置 1–60 秒；加 `--once` 只读取一次。前台持续运行时用 Ctrl+C 停止，不会安装服务或定时任务。

工作台使用相同根和用户，刷新即可查看新来源与习惯。监听器不会从文件自行选择用户身份、读取其他宿主数据库，或给自己开放账号历史访问权。

## 执行三会话示例

```python
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile

# Run from the package directory. This writes synthetic data only.
area = Path(tempfile.mkdtemp(prefix="selected-feed-demo-"))
feed, profile = area / "selected.jsonl", area / "private-profile"
feed.touch()
context = "writing"
now = dt.datetime.now(dt.timezone.utc)
for session in range(1, 4):
    conversation = {
        "session_id": f"feedback-{session}", "context": context,
        "messages": [{"id": "correction", "role": "user",
                      "text": "Too long. Please keep it brief.",
                      "at": (now - dt.timedelta(days=session)).isoformat()}]
    }
    with feed.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(conversation) + "\n")
    subprocess.run([sys.executable, "-B", "scripts/watch_conversations.py",
                    "--root", str(profile), "--subject", "demo",
                    "--enable-conversations", "--input", str(feed), "--once"],
                   check=True)

result = subprocess.run(
    [sys.executable, "-B", "scripts/host.py", "--root", str(profile),
     "--subject", "demo", "call", "profile_habits"],
    input=json.dumps({"context": context}), text=True, capture_output=True, check=True)
habits = json.loads(result.stdout)
assert any(item["status"] == "ready_to_review" for item in habits["candidates"])
print(json.dumps(habits, indent=2))
print("Synthetic files:", area)
```

示例每追加一条记录就重新启动一次导入器，因此实际走过了保存位置和重启。结束时只有待审习惯，没有已接受规则。查看返回原文，确认它确实代表你希望保留的偏好后再采用。测试中文反馈时，可把合成文本替换为 `太长了，请简短一点。`。

## 状态与恢复

| 状态或错误 | 含义和处理 |
|---|---|
| `caught_up` | 当前可用的完整记录已经处理。 |
| `waiting_for_line` | 最后一条缺少末尾换行，写完再处理；半条记录不算导入成功。 |
| `paused` | 档案已暂停，未读位置不前移；合适时再恢复。 |
| `INVALID_JSONL` / 导入拒绝 | 第一条失败完整记录未被消费。修复尚未处理的记录或核实来源，后续不会被静默跳过。 |
| `FEED_HISTORY_CHANGED` | 已处理字节被修改或截断，应恢复原始前缀，不要重置游标掩盖变化。 |
| `WATCH_BUSY` | 另一导入器持有占用。怀疑遗留占用时，先核实原进程已经停止，再明确恢复。 |

文件最多 4 MiB，单记录最多 1 MB，每用户最多 16 个选定文件。轮换前先审查保留状态；新路径是新选定文件，不是重放已遗忘来源的授权。档案本身仍限制会话和消息数量。

## 审查、纠正和保留

`profile_habits` 展示状态、原文、支持与反对证据；`profile_habit_review` 根据本人实际决定接受或忽略当前可审候选。当前明确偏好与纠正优先。

导入文本仍受既有对话保留范围约束。暂停停止普通学习；删除来源会连带清理相关习惯、规则、已准备方案和评价。重置后保留监听进度与哈希，避免已处理文本被意外重导入；游标不保存对话正文。用户选定的原文件在存储之外，不会被档案删除操作移除。

当前识别器在已经暴露的回归集合中覆盖 22/22 个正例，但首次未见 `fresh-v4` 测试只覆盖 1/8（英文 1/4，中文 0/4），8 个负例中没有错误建议。最初 0/6 的失败也保留。这是实验性的表达线索识别，不是对用户行为的普遍理解。上面的简单示例验证导入与审阅路径，语言覆盖需另看[当前验收](evaluation.zh-CN.md)。

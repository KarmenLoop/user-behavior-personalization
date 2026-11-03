# 本地工具参考 — v0.5.1

[English](tools.en.md) · [中文](tools.zh-CN.md)

CLI、MCP 标准输入输出和本地工作台共用同一适配器。身份由 `--subject` 固定，工具参数不能切换用户。运行时提供 **25 个工具**，完整 JSON schema 以 `scripts/host.py` 为准。

| 工具 | 参数（`?` 为可选） | 用途 |
|---|---|---|
| `profile_read` | `context` | 读取已确认规则。 |
| `profile_correct` | `expected_revision, rule` | 保存明确偏好或纠正。 |
| `profile_pause` | `expected_revision, paused` | 暂停或恢复常规使用。 |
| `profile_forget` | `expected_revision, rule_id` | 删除规则及相关证据。 |
| `profile_export` | `—` | 查看私有状态，暂停后仍可使用。 |
| `profile_observe` | `expected_revision, event` | 记录授权的结构化反馈。 |
| `profile_insights` | `context` | 查看结构化反馈候选。 |
| `profile_review` | `expected_revision, candidate_id, decision, source_id` | 审阅结构化候选。 |
| `profile_forget_observations` | `expected_revision, observation_ids` | 删除观察记录及依赖规则。 |
| `profile_reset` | `expected_revision` | 清空内容并暂停。 |
| `conversation_import` | `expected_revision, conversation` | 导入一个已授权的完整会话快照。 |
| `profile_proposal_review` | `expected_revision, proposal_id, decision, source_id; replace_rule_id?` | 审阅开放文本提议，可明确替换旧规则。 |
| `profile_portrait` | `context` | 查看确认偏好、提议与写作观察。 |
| `profile_forecast` | `context, request` | 实验性的历史后续请求检索。 |
| `profile_forget_conversation` | `expected_revision, session_id` | 删除会话及派生内容。 |
| `profile_forget_messages` | `expected_revision, source_keys` | 删除选定来源消息及依赖内容。 |
| `profile_model_context` | `context` | 为宿主模型构建本地来源上下文。 |
| `profile_model_propose` | `expected_revision, proposals` | 校验原文引用并暂存提议。 |
| `profile_habits` | `context` | 从重复反馈中发现习惯，附证据与冲突。 |
| `profile_habit_review` | `expected_revision, context, candidate_id, decision, source_id` | 审阅达到门槛的会话习惯候选。 |
| `profile_plan` | `context, task; task_overrides?, omit_rule_ids?, max_preference_chars?` | 预览实际任务提示选择，不写入、不调用模型。 |
| `profile_plan_prepare` | `expected_revision + profile_plan fields` | 保存方案记录，便于后续评价。 |
| `profile_outcome` | `expected_revision, plan_id, source_id, rating, basis` | 记录用户明确评价。 |
| `profile_outcome_summary` | `context` | 按评价依据与规则版本查看汇总。 |
| `profile_plan_forget` | `expected_revision, plan_id` | 删除方案及其评价。 |

## 版本与决定

写入前用 `profile_read` 或 `profile_export` 读取当前版本。遇到 `REVISION_CONFLICT` 后，重新读取并核对变更，不要盲目重放旧决定。审阅结果为 `accept` 或 `reject`。来源标识只是宿主提供的记录，并非用户同意的独立证明。

会话收集需要 `--enable-conversations`；结构化事件收集另需 `--enable-observations`。候选经审阅前不会成为有效规则。可执行例子见[会话指南](conversation-guide.zh-CN.md)和[结构化反馈指南](structured-feedback.zh-CN.md)。

## 为本次任务设置例外

以下只读调用不需要版本号，也不会改变已保存偏好：

```sh
printf '%s' '{"context":"writing","task":"Explain the release tradeoffs.","task_overrides":{"response_length":"detailed"}}' | \
  python3 -B scripts/host.py --root ../private-profile --subject owner call profile_plan
```

`task_overrides` 支持下列六种协作维度。`omit_rule_ids` 最多接受 30 个已有规则标识；`max_preference_chars` 为 200–12000，默认 4000。显式设置优先于从任务文本识别出的要求。`build_context.py` 和 `run_host.py` 分别通过 `--override`、`--omit-rule` 与 `--preference-budget` 使用相同选项。

| Dimension | Values |
|---|---|
| `response_length` | `concise`, `balanced`, `detailed` |
| `structure` | `conclusion_first`, `steps`, `examples`, `code_first`, `bullets` |
| `teaching` | `explain_back`, `worked_example`, `practice` |
| `initiative` | `ask_first`, `suggest_next` |
| `workflow_next_step` | `clarify`, `plan`, `implement`, `test`, `review`, `summarize` |
| `language` | `en`, `zh` |

## 保存与评价方案

`profile_plan_prepare` 使用相同字段，并增加最新版本号。将返回的 `plan.plan_id` 传给 `profile_outcome`，写入前再次读取当前版本。`rating` 为 `helpful`、`unhelpful`、`mixed` 或 `not_sure`；`basis` 为 `prompt_review` 或 `response_use`。后者记录用户报告的回答使用情况，不会独立验证模型已执行。

每个用户最多保存 100 个方案。每个方案只有一个当前评价，更新评价是替换而非新增一票；评价来源历史最多保留 100 次修改。用 `profile_plan_forget` 删除方案及相关评价。只做预览不会保存任务文本或方案记录。

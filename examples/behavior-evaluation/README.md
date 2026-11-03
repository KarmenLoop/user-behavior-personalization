# Behavior learning diagnostics / 行为学习诊断

These small synthetic conversations check whether repeated user corrections
produce reviewable preferences. They are not a benchmark of real-user benefit.
Inputs and expected answers were frozen separately before each evaluation.
The manifests retain their original byte hashes. Earlier failures remain in
[`docs/evaluation-results-v0.5.0.json`](../../docs/evaluation-results-v0.5.0.json).

Run with Python 3.11 or newer from the repository root:

```sh
python3 scripts/evaluate_behavior.py
python3 scripts/evaluate_behavior.py --suite all --require-all --output ../behavior-evaluation.json
```

The default suite is `fresh-v4`. Each case uses actual host imports and habit
discovery in a fresh disposable SQLite store. The evaluator fixes the clock to
the fixture date; it does not replace the learner, storage, or authorization
checks. No provider is called. Labels are used for scoring after discovery;
they are not passed to the learner.

Only `ready_to_review` candidates count as offers. Coverage, precision among
offers, and false offers on negative controls are reported separately. No
offers means undefined precision. `--require-all` returns exit code 1 when a
positive is missed, an incorrect extra preference is offered, or a control fails. Invalid inputs or changed source files
return exit code 2. An output file must be outside the repository and must not
already exist; without `--output`, the report is printed as JSON.

Do not tune the learner on these held-out answers. Once results inform a
change, keep the old results and use a separately authored unseen suite to
check the next revision. Reruns evaluate the current checkout; source hashes
in historical results identify the earlier recorded versions.

The initial, fresh-v2, and fresh-v3 cases have since been exposed during
development. Their current 22/22 positive result is a regression check, not
unseen evaluation. The separate first fresh-v4 evaluation covered 1/8 positives
(English 1/4, Chinese 0/4), with no offers on its eight negative controls.
One correct offer is too little evidence for a broad accuracy claim.
`--suite all` runs both groups; keep their results separate. A public-runner
reproduction of fresh-v4 is recorded separately from its first evaluation.

这些小型合成会话用于检查：用户反复纠正之后，系统能否提出需要本人确认的偏好。
它们不能证明真实用户的体验改善。每套输入和答案均在评估前分别冻结，清单保留
原始字节哈希，之前的失败结果也会继续保留。

在仓库根目录使用 Python 3.11 或更新版本运行上面的命令。默认评估 `fresh-v4`。
每个案例都会使用新的临时 SQLite 存储，通过真实宿主导入会话并发现习惯。
评估器仅将时钟固定到案例日期，不替换学习器、存储或授权检查，也不调用模型服务。
预期答案只参与最后评分，不会传给学习器。

只有 `ready_to_review` 候选计入实际建议。报告分别列出正例覆盖率、已提出建议中的
准确率，以及负例的错误建议率。没有提出建议时，准确率无法计算。使用
`--require-all` 后，漏掉正例、多提出了错误偏好或边界检查失败都会返回退出码 1；输入无效或运行期间
源码发生变化返回退出码 2。输出文件必须位于仓库外且尚不存在；不指定文件时，
报告会作为 JSON 输出。

请勿用这些保留答案调参。结果一旦参与改进，就应保留原有失败记录，并另外编写
未见过的案例检验下一次修订。重新运行评估器检查的是当前源码；历史结果中的
源码哈希用于标识当时记录的版本。

initial、fresh-v2 和 fresh-v3 的案例随后已经用于开发，因此当前 22/22 的正例结果
属于已知案例回归检查，不能当作未见数据测试。另行编写的 fresh-v4 首次评估只覆盖
1/8 个正例（英文 1/4，中文 0/4），八个负例均未提出偏好建议。仅一个正确建议不足以
证明广泛准确性。`--suite all` 会运行这两组案例，但结果应分别解读。公开评估器对
fresh-v4 的复现记录与首次测试记录分开保存。

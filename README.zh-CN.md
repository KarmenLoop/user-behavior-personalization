# 用户行为个性化

[English](README.md) · [中文](README.zh-CN.md) · **v0.7.0**

“先给能复现问题的输入，再给修改方式”，应该影响下一次排错回答，也应该在给客户写邮件时让位于那个场景的需求。

这个本地工作台从你选择的对话片段中提炼偏好，由你确认，再用于条件匹配的任务。你可以直接比较两份真实模型回答，分别记录更喜欢哪份、哪些内容有误。

![v0.7.0 工作台中的两份真实模型回答](docs/images/actual-comparison-v0.7.0.zh-CN.jpg)

*真实浏览器截图，使用合成反馈和 Python 排错任务。两份回答来自已配置的 Codex 模型；投票或主动揭示前隐藏身份。原始回答保留生成时的语言，切换界面语言不会改写回答。*

[下载 v0.7.0](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.7.0) · [完整操作教程](docs/semantic-learning.zh-CN.md) · [当前评估](docs/evaluation.zh-CN.md) · [六项路线图](docs/roadmap.zh-CN.md)

## 在本机开始

下载、核对并解压发布包。需要 Python **3.11+**，本地运行没有第三方 Python 依赖。

```sh
python3 -B scripts/check_package.py
python3 -B scripts/workspace.py --root ../private-profile --subject demo --enable-conversations
```

打开终端打印的本地地址。这会启动离线工作台：导入获准使用的对话，审核明确偏好与反复反馈，检查任务提示，管理私有档案。这些步骤无需模型账号。[先体验离线教程](docs/tutorial.zh-CN.md)。

需要语义提炼和真实回答对比时，安装并登录兼容的 Codex CLI，指定自己的模型后重新启动：

```sh
python3 -B scripts/workspace.py --root ../private-profile --subject demo \
  --enable-conversations --enable-models --model YOUR_MODEL
```

已验收客户端为 `codex-cli 0.165.0-alpha.1.2`；工具关闭能力不兼容时会拒绝调用。macOS 可用 `--system-proxy` 选择既有的固定回环代理，只影响模型子进程环境。

1. 导入你有权使用的对话，勾选本次要分析的原文，再点击**分析选中片段**。只有所选片段与相关的已确认偏好会发送给已配置的 Codex 账号。
2. 查看每项提案及精确引用。可以明确替换某条旧规则，也可以单独保留。模型提案未经审核不会生效。
3. 进入**用于下一次任务**，选择适用的任务类型、受众和阶段，预览偏好被采用或排除的原因。
4. 点击**比较真实回答**。同一模型使用同一任务、判断规则和临时要求回答两次，其中一组加入适用的已保存偏好。A/B 身份与调用顺序随机分配。
5. 选择 A、B、平局或都不选，并单独报告正确性。投票会揭示身份并记录体验，不会修改事实结论或自动确认规则。

## 可以看清哪些变化

**不只识别固定句式。** 可选语义路径可以解释间接反馈，每项提案保留所选原文与条件。仅导入或刷新不会触发模型发送。离线线索学习器继续保留，过去的漏识别也继续公开。

**偏好有适用范围。** 工作场景、任务类型、受众、阶段、过期时间、暂不采用的规则与临时控制共同决定本次内容。缺少条件就不匹配；同等具体的结构化偏好发生冲突时暂不采用。任意自由文本之间的冲突仍需审核。

**看到实际回答，也能检查提示。** 两种视图使用同一套选择逻辑。私有对比保留模型、客户端和偏好版本，揭示前隐藏每组执行元数据。失败、暂停或版本过期的请求不会保存半份对比。

**评价有明确边界。** 偏好投票、正确性报告、提示方案评分分开记录。提前揭示后再投票，会标注为非盲评；偏好改写后不继承旧评分。不训练模型权重，也不把好评当作事实正确的证据。

**先看证据，再决定是否赞同。** 用户的解释和诊断先作为假设，两组都保留验证、反例、未知信息与有依据纠正的要求。这些约束不能证明模型迎合已经消除。[判断规则与限制](docs/independent-judgment.zh-CN.md)。

## 档案由你控制

档案及最多 20 组私有回答保存在包外的专用 SQLite 目录。暂停会隐藏普通证据和回答，丢弃已过期的进行中结果。遗忘来源会删除依赖它的规则、方案、回答与反馈；重置清除档案内容并保持暂停。提供方历史、终端记录、外部备份仍有各自的保留范围。[存储与删除说明](docs/privacy-and-memory-control.zh-CN.md)。

已选文件监听、自由文本偏好、本人目标、表达观察和实验性历史后续请求检索继续提供。监听器只跟随指定的获准文件，不会抓取账号。[格式与恢复](docs/automatic-learning.zh-CN.md) · [对话工具](docs/conversation-guide.zh-CN.md)。

Codex、Cursor 可以使用既有 MCP 配置助手或调用包装入口；`build_context.py` 为自有客户端生成限定上下文，也适用于 DeepSeek 类 API。更完整的原生宿主接入与持续多轮评估仍列在[路线图](docs/roadmap.zh-CN.md)，写好配置不等于模型已经实际使用。

## 核对验收

[当前评估](docs/evaluation.zh-CN.md)分别记录提供方调用、语义提案核对、本地运行检查和真实用户效果。旧的未见改写 **1/8** 结果及调用失败全部保留。v0.7.0 语义案例是本轮自行编写的合成验收数据，不是新的独立泛化准确率。

- [语义学习教程](docs/semantic-learning.zh-CN.md) / [English](docs/semantic-learning.en.md)：启动、选原文、审核、条件、真实回答与删除。
- [离线教程](docs/tutorial.zh-CN.md)、[宿主接入](docs/host-integration.zh-CN.md)与 [30 个工具](docs/tools.zh-CN.md)。
- [模型验收](docs/model-checks.zh-CN.md)、[研究依据](docs/research.zh-CN.md)与 [20 个实际问题](docs/faq.zh-CN.md)。

[Apache-2.0](LICENSE) · [KarmenLoop](https://karmenloop.com) · [支持](SUPPORT.md) · [安全](SECURITY.md)

历史介绍：[v0.2.0](docs/overview-v0.2.0.zh-CN.md)、[v0.3.0](docs/overview-v0.3.0.zh-CN.md)、[v0.4.0](docs/overview-v0.4.0.zh-CN.md)、[v0.6.0](docs/overview-v0.6.0.zh-CN.md)。

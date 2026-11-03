# 用户行为个性化

[English](README.md) · [中文](README.zh-CN.md) · **v0.5.0**

你已经三次要求回答短一点，但下一件事又需要详细解释。助手应该记住习惯，也能处理例外。

这个本地工作台把反复出现的反馈整理为可审查的偏好，让你看见它怎样改变下一次任务的提示内容，再记录这次调整是否有帮助。一次性的选择不会改掉长期习惯。

![v0.5.0 真实工作台：原始依据与两项待审核习惯](docs/images/workspace-v0.5.0.zh-CN.jpg)

*真实工作台截图，使用合成反馈。三个选定会话形成了两项待审核习惯。*

[下载](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.5.0) · [完整教程](docs/tutorial.zh-CN.md) · [自动学习](docs/automatic-learning.zh-CN.md) · [当前验收](docs/evaluation.zh-CN.md)

## 先走完一次闭环

需要 Python **3.11+**。下载、核对并解压后运行：

```sh
python3 -B scripts/workspace.py --root ../private-profile --subject demo --enable-conversations
```

打开终端打印的 `http://127.0.0.1:...` 地址。工作台在本机运行，无需模型账号。

1. 点击**体验一个合成示例**，导入三个独立会话中的“太长了，请简短一点”。
2. 查看简洁回答候选习惯的来源，再选择**保留这项偏好**。
3. 进入**用于下一次任务**，输入任务，预览已保存偏好进入提示后的变化。
4. 在**仅用于这次任务**中选择详细回答，再次预览：本次改用临时要求，长期的简洁偏好仍保留。
5. 保存方案，评价查看提示是否有帮助。通过宿主实际使用模型回答后，再单独记录真实使用反馈。

## 这次真正补上了什么

**反复纠正能变成可用习惯。** 从选择的对话或追加文件中，识别中英文反馈线索，按独立会话整理支持与反对证据，附上原文。明确偏好可以立即审核，反复习惯需要一致的多次支持。

**能看见实际变化。** 工作台、上下文生成器和宿主包装入口共用偏好选择逻辑。预览解释采用了什么、排除了什么及其原因，不用虚构的前后回答充当效果。

**临时要求只影响本次。** 任务控制、暂不使用的规则、场景、过期时间和偏好内容预算共同决定传入内容，预览不会改动永久档案。

**反馈对应真正使用的版本。** 有帮助、部分有用、没帮助、不确定，都关联已准备方案和具体偏好版本。规则改写后不继承旧评价；沉默和命令成功都不算认可。

## 换成自己的对话

在工作台导入 JSON 对话，也可以运行：

```sh
python3 -B scripts/watch_conversations.py --root ../private-profile --subject owner \
  --enable-conversations --input /path/to/selected.jsonl
```

每一完整行是一份**完整会话快照**，不是单条消息。前台监听器只处理指定文件的新行，保留重启位置，遇到拒绝的记录就停在该处。它不会搜索账号历史，也不安装后台服务。格式与恢复方法见[自动学习指南](docs/automatic-learning.zh-CN.md)。

自动识别仍是实验功能，常见改写也可能漏掉。请核对来源，必要时直接纠正偏好；[公开评估](docs/evaluation.zh-CN.md)同时记录成功建议与漏识别。

已有能力继续保留：自由文本偏好、项目术语、本人目标、表达观察、可选模型提案，以及实验性的历史后续请求检索。后者的英文改写覆盖仍弱，不应与新的习惯学习混为一谈。

## 接到实际宿主

Codex、Cursor 可使用 MCP 配置助手或调用前包装入口。`build_context.py` 为自己的模型客户端生成限定上下文，也适用于 DeepSeek 类聊天 API；包本身不会自行发送提供方请求。

浏览器预览是已经实现的本地功能，但**不代表模型回复验收成功**：本轮 v0.5.0 Codex 尝试在 80 秒后超时。能力和分数的实际依据见[宿主验收与学习诊断](docs/evaluation.zh-CN.md)。

## 继续深入

- [教程](docs/tutorial.zh-CN.md) / [English](docs/tutorial.en.md)：下载、工作台、审核、临时调整、反馈和删除。
- [自动学习](docs/automatic-learning.zh-CN.md)：选定文件、证据、冲突、重启与错误处理。
- [宿主接入](docs/host-integration.zh-CN.md)：Codex、Cursor、模型上下文与 [25 个工具](docs/tools.zh-CN.md)。
- [对话指南](docs/conversation-guide.zh-CN.md)：JSON/JSONL、自由文本提案、档案及历史检索。
- [隐私](docs/privacy-and-memory-control.zh-CN.md)、[研究依据](docs/research.zh-CN.md)与 [20 个实际问题](docs/faq.zh-CN.md)。

档案保存在包外的私有 SQLite 中，支持暂停、查看、纠正、遗忘与重置。工作台可切换中英文，本地运行只需 Python 标准库与原生浏览器资源。

[Apache-2.0](LICENSE) · [KarmenLoop](https://karmenloop.com) 开发 · [支持](SUPPORT.md) · [安全](SECURITY.md)

历史介绍：[v0.2.0](docs/overview-v0.2.0.zh-CN.md)、[v0.3.0 中间源码](docs/overview-v0.3.0.zh-CN.md)、[v0.4.0](docs/overview-v0.4.0.zh-CN.md)。

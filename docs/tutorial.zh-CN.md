# User Behavior Personalization · 用户偏好记录: 使用指南

[English](tutorial.en.md) | 简体中文 · [项目首页](../README.zh-CN.md)

本指南对应 **v0.1.1**.

## 1. 下载与校验

从发行页下载 [`user-behavior-personalization-v0.1.1.zip`](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.1.1)，同时保留校验文件或 manifest。比较完整 SHA-256 后再解压：macOS 使用 shasum -a 256，Linux 使用 sha256sum，PowerShell 使用 Get-FileHash -Algorithm SHA256。校验只能证明字节一致，预期哈希本身也需要可信来源。

## 2. 安装与加载

解压 ZIP，在顶层目录运行 python3 scripts/install_skill.py --destination ../installed-skills/user-behavior-personalization。目标必须是源目录外的新目录，再通过宿主支持的加载方式选择它。

刷新宿主发现或开启新会话，明确读取已安装的 SKILL.md，并核对上面版本。不需要为技能另开模型账号；宿主使用自己的模型、工具与权限。

## 3. 配置与第一项任务

由宿主明确 PROFILE_ROOT、USER_ID、USER_TIMEZONE、MEMORY_ENABLED、CONVERSATION_SOURCE、REFLECTION_TRIGGER。这些是集成约定字段，不是附带程序会读取的环境变量。使用私有用户目录里的空白模板开始。

使用含明确更正的合成对话，让宿主提出对应范围的偏好并展示来源，只通过现有且已授权的操作保存，再从已保存记录验证后续读取。

## 4. 进一步实践

检查一次冲突更正，再通过真实宿主测试导出或删除。仓库检查确保模板空白及包内容规范，不代表已通过真实用户或跨设备全链路认证。

保留当前版本、真实命令、退出码、结果与未验证限制。使用合成数据做首次检查。

## 5. 排错、升级与移除

宿主找不到技能时，先检查配置的技能根目录和 SKILL.md 可读性。哈希不一致时停止使用该包并重新核对下载；不要跳过错误。

升级前完成当前写入，分别备份技能与私人任务数据。将新版本解压到新目录，核对后再切换；回退时恢复旧技能，保留较新的用户数据与证据。卸载只移除对应技能目录或发现入口；如曾另行注册调度，应在真实宿主中取消并确认。

## 6. 许可证

[Apache-2.0](../LICENSE). 此处提供简明用户指南；具体使用和再分发条件以许可证原文为准。

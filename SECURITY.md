# 安全策略

## 支持范围

当前项目处于 MVP 阶段，主要覆盖以下 LLM 安全风险：

- Prompt Injection
- Jailbreak
- Sensitive Information Disclosure
- Tool Abuse
- RAG Poisoning

## 漏洞反馈

如果发现安全问题，请通过 GitHub Issue 反馈，并在标题中标注 `[Security]`。

提交 Issue 时请尽量包含：

- 影响的模块或接口
- 复现步骤
- 预期行为和实际行为
- 可能的影响范围
- 建议修复方式

请不要在公开 Issue 中提交真实 API Key、访问令牌、个人身份信息或内部系统提示词。

## 说明

本项目不是完整生产级安全网关。生产使用前仍需要补充认证、权限控制、限流、监控、告警、密钥管理和更严格的策略审计。

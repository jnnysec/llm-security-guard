# Threat Model

## 资产

- 用户Prompt
- System Prompt
- 企业知识库
- API Key
- Tool权限

---

## 攻击面

### Prompt Injection

攻击目标：

绕过系统规则

风险：

High

---

### Jailbreak

攻击目标：

解除模型限制

风险：

High

---

### Data Leakage

攻击目标：

泄露敏感数据

风险：

Critical

---

### Tool Abuse

攻击目标：

滥用Agent工具

风险：

Critical

---

### RAG Poisoning

攻击目标：

污染知识库

风险：

Critical

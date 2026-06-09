# 系统架构设计

## 整体架构

User
 ↓
Input Guardrail
 ↓
LLM Gateway
 ↓
Output Guardrail
 ↓
Audit Service
 ↓
Dashboard

---

## 输入护栏

### Rule Engine

- 黑名单
- 正则规则
- OWASP LLM Top10规则

### ML Engine

- BERT分类器
- Qwen Embedding分类器

---

## 输出护栏

### PII检测

- 手机号
- 邮箱
- 身份证
- API Key

### Risk Score

最终输出：

0-100分

---

## 存储层

PostgreSQL

表：

- request_logs
- attacks
- scores
- templates

Redis

- blacklist cache
- request cache

---

## 可观测性

Prometheus

Grafana

OpenTelemetry

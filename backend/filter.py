from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple

from backend.classifier import classifier
from backend.config import settings
from backend.db import store


@dataclass(frozen=True)
class Rule:
    name: str
    risk_type: str
    pattern: str
    severity: int
    description: str


RULES = [
    Rule(
        name="prompt_injection_override",
        risk_type="Prompt Injection",
        pattern=r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions|忽略.*(之前|上面|系统).*(指令|规则|提示)",
        severity=55,
        description="尝试覆盖系统或开发者指令",
    ),
    Rule(
        name="system_prompt_exfiltration",
        risk_type="System Prompt Leakage",
        pattern=r"(reveal|dump|print|show).*(system|developer).*(prompt|message)|(泄露|输出|显示).*(系统提示|开发者消息|内部规则)",
        severity=60,
        description="尝试获取系统提示词或内部规则",
    ),
    Rule(
        name="jailbreak",
        risk_type="Jailbreak",
        pattern=r"\bDAN\b|jailbreak|developer\s+mode|越狱|绕过.*(限制|安全|审查)|无限制模式",
        severity=55,
        description="越狱或解除安全限制请求",
    ),
    Rule(
        name="unsafe_code_execution",
        risk_type="Tool Abuse",
        pattern=r"import\s+os|subprocess|os\.system|eval\s*\(|exec\s*\(|rm\s+-rf|curl\s+https?://|wget\s+https?://",
        severity=60,
        description="危险代码执行或工具滥用请求",
    ),
    Rule(
        name="credential_request",
        risk_type="Data Leakage",
        pattern=r"(api[_ -]?key|access[_ -]?token|secret[_ -]?key|password|私钥|密钥|访问令牌|密码).*(给我|输出|泄露|dump|show|print)?",
        severity=55,
        description="请求凭证、密钥或访问令牌",
    ),
    Rule(
        name="rag_poisoning",
        risk_type="RAG Poisoning",
        pattern=r"(污染|篡改|覆盖).*(知识库|向量库|检索结果)|poison.*(rag|retrieval|vector)",
        severity=50,
        description="尝试污染 RAG 知识库或检索结果",
    ),
]


def analyze_prompt(prompt: str) -> Dict[str, Any]:
    matches: List[Dict[str, Any]] = []
    risk_types: List[str] = []
    risk_score = 0
    prompt_lower = prompt.lower()

    for word in store.blacklist():
        if word.lower() in prompt_lower:
            matches.append(
                {
                    "source": "blacklist",
                    "name": word,
                    "risk_type": "Blacklist",
                    "severity": 55,
                    "description": f"命中黑名单关键字: {word}",
                }
            )
            risk_types.append("Blacklist")
            risk_score += 55

    for rule in RULES:
        if re.search(rule.pattern, prompt, re.IGNORECASE):
            matches.append({"source": "rule", **asdict(rule)})
            risk_types.append(rule.risk_type)
            risk_score += rule.severity

    model_result = classifier.classify(prompt)
    if model_result.risk_score >= settings.classifier_threshold:
        matches.append(
            {
                "source": "classifier",
                "name": model_result.label,
                "risk_type": "Local Classifier",
                "severity": model_result.risk_score,
                "description": f"本地分类器判定为 {model_result.label}",
                "features": model_result.features,
                "confidence": model_result.confidence,
            }
        )
        risk_types.append("Local Classifier")
        risk_score += model_result.risk_score

    risk_score = min(risk_score, 100)
    safe = risk_score < 50
    unique_risks = sorted(set(risk_types))
    reason = "安全" if safe else "；".join(match["description"] for match in matches[:3])

    return {
        "safe": safe,
        "score": 100 - risk_score,
        "risk_score": risk_score,
        "reason": reason,
        "risk_types": unique_risks,
        "matches": matches,
        "classifier": asdict(model_result),
    }


def filter_input(prompt: str) -> Tuple[bool, str]:
    result = analyze_prompt(prompt)
    return bool(result["safe"]), str(result["reason"])

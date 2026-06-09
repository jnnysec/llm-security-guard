from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ClassifierResult:
    label: str
    risk_score: int
    confidence: float
    features: List[str]


class LocalPromptClassifier:
    """Small, deterministic classifier that can be replaced by an ML model later."""

    FEATURE_WEIGHTS: Dict[str, int] = {
        "instruction_override": 28,
        "secret_exfiltration": 30,
        "tool_abuse": 24,
        "jailbreak_roleplay": 24,
        "unsafe_code": 22,
        "credential_language": 18,
        "obfuscation": 12,
    }

    FEATURE_PATTERNS = {
        "instruction_override": [
            r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
            r"disregard\s+(the\s+)?(system|developer)\s+message",
            r"忽略.*(之前|上面|系统|开发者).*(指令|规则|提示)",
            r"不要遵守.*(规则|限制|安全策略)",
        ],
        "secret_exfiltration": [
            r"(reveal|dump|print|show).*(system|developer).*(prompt|message)",
            r"(leak|exfiltrate|steal).*(secret|key|token|credential)",
            r"(泄露|输出|显示|告诉我).*(系统提示|密钥|token|凭证|内部规则)",
        ],
        "tool_abuse": [
            r"(use|call|invoke).*(shell|terminal|browser|tool).*without",
            r"(执行|调用).*(工具|shell|终端|命令)",
            r"(curl|wget)\s+https?://",
        ],
        "jailbreak_roleplay": [
            r"\bDAN\b",
            r"jailbreak",
            r"developer\s+mode",
            r"(越狱|绕过|无限制模式|开发者模式)",
        ],
        "unsafe_code": [
            r"eval\s*\(",
            r"exec\s*\(",
            r"import\s+os",
            r"subprocess",
            r"os\.system",
            r"rm\s+-rf",
        ],
        "credential_language": [
            r"api[_ -]?key",
            r"access[_ -]?token",
            r"secret[_ -]?key",
            r"password",
            r"(账号|密码|私钥|访问令牌)",
        ],
        "obfuscation": [
            r"base64",
            r"rot13",
            r"hex\s+encode",
            r"(编码|混淆|拆分字符)",
        ],
    }

    def classify(self, prompt: str) -> ClassifierResult:
        matched_features: List[str] = []
        score = 0

        for feature, patterns in self.FEATURE_PATTERNS.items():
            if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in patterns):
                matched_features.append(feature)
                score += self.FEATURE_WEIGHTS[feature]

        score = min(score, 100)
        label = "malicious" if score >= 55 else "suspicious" if score >= 30 else "benign"
        confidence = round(score / 100, 2)
        return ClassifierResult(label=label, risk_score=score, confidence=confidence, features=matched_features)


classifier = LocalPromptClassifier()

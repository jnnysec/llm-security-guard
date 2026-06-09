from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class SensitivePattern:
    issue: str
    pattern: str
    replacement: str
    severity: int


PATTERNS = [
    SensitivePattern("手机号", r"(?<!\d)1[3-9]\d{9}(?!\d)", "***********", 35),
    SensitivePattern("身份证", r"(?<!\d)\d{17}[\dXx](?!\d)", "******************", 40),
    SensitivePattern(
        "邮箱",
        r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9._%+-])",
        "***@***",
        25,
    ),
    SensitivePattern(
        "密钥",
        r"\b(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})\b",
        "[REDACTED_KEY]",
        45,
    ),
    SensitivePattern(
        "令牌",
        r"(?i)\b(access[_-]?token|api[_-]?key|secret[_-]?key|password)\s*[:=]\s*[\"']?[^\"'\s,;]{8,}",
        "[REDACTED_SECRET]",
        45,
    ),
]


def audit_output(text: str) -> Dict[str, Any]:
    issues: List[str] = []
    findings: List[Dict[str, Any]] = []
    safe_text = text
    penalty = 0

    for item in PATTERNS:
        matches = list(re.finditer(item.pattern, safe_text, re.IGNORECASE))
        if not matches:
            continue
        issues.append(item.issue)
        findings.append(
            {
                **asdict(item),
                "count": len(matches),
            }
        )
        penalty += item.severity
        safe_text = re.sub(item.pattern, item.replacement, safe_text, flags=re.IGNORECASE)

    score = max(100 - penalty, 0)
    return {
        "safe_text": safe_text,
        "score": score,
        "issues": sorted(set(issues)),
        "findings": findings,
        "safe": score >= 70,
    }

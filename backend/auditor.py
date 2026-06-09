import re
from typing import Dict

def audit_output(text: str) -> Dict:
    issues = []
    safe_text = text
    phone_pattern = r"\b\d{11}\b"
    id_pattern = r"\b\d{17}[\dXx]\b"
    if re.search(phone_pattern, text):
        issues.append("手机号")
        safe_text = re.sub(phone_pattern, "***********", safe_text)
    if re.search(id_pattern, text):
        issues.append("身份证")
        safe_text = re.sub(id_pattern, "*****************", safe_text)
    score = 100 - len(issues) * 50
    score = max(score, 0)
    return {"safe_text": safe_text, "score": score, "issues": issues}

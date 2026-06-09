import re
from typing import Tuple

BLACKLIST = ["eval", "exec", "curl", "wget", "os.system"]

def filter_input(prompt: str) -> Tuple[bool, str]:
    # 黑名单匹配
    for word in BLACKLIST:
        if word in prompt.lower():
            return False, f"黑名单关键字: {word}"
    # 正则规则匹配
    patterns = [r"import\s+os", r"subprocess"]
    for pat in patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            return False, f"匹配正则: {pat}"
    # 简单小模型占位（可替换真实分类器）
    if "敏感" in prompt:
        return False, "小模型判定不安全"
    return True, "安全"

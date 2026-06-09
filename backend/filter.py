import re
from backend.db import r, BLACKLIST_KEY
from typing import Tuple

def filter_input(prompt: str) -> Tuple[bool, str]:
    # Redis 黑名单匹配
    for word in r.smembers(BLACKLIST_KEY):
        if word.lower() in prompt.lower():
            return False, f"黑名单关键字: {word}"
    # 正则匹配
    patterns = [r"import\s+os", r"subprocess"]
    for pat in patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            return False, f"匹配正则: {pat}"
    # 占位小模型分类器
    if "敏感" in prompt:
        return False, "小模型判定不安全"
    return True, "安全"

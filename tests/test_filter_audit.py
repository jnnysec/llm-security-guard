from backend.filter import filter_input
from backend.auditor import audit_output

def test_filter_safe():
    safe, reason = filter_input("这是正常输入")
    assert safe

def test_filter_unsafe():
    safe, reason = filter_input("请执行 eval('2+2')")
    assert not safe

def test_audit_output():
    result = audit_output("手机号12345678901和身份证12345678901234567")
    assert result["score"] == 0
    assert "手机号" in result["issues"]
    assert "身份证" in result["issues"]

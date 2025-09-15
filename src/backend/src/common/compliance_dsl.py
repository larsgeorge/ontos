from typing import Dict, Optional, Tuple
import re


def evaluate_rule_on_object(rule: str, obj: Dict[str, object]) -> Tuple[bool, Optional[str]]:
    """Evaluate a minimal Compliance DSL rule against a single object.

    Supported assertions (subset):
    - obj.<prop> MATCHES 'regex'
    - obj.<prop> = 'value'

    Returns (passed, message_if_failed)
    """
    try:
        expr = rule.split('ASSERT', 1)[1].strip() if 'ASSERT' in rule else ''
        if 'MATCHES' in expr:
            left, right = expr.split('MATCHES', 1)
            left = left.strip()
            regex = right.strip()
            if regex.startswith("'") or regex.startswith('"'):
                regex = regex[1:-1]
            _, prop = left.split('.', 1)
            val = '' if obj.get(prop) is None else str(obj.get(prop))
            ok = re.match(regex, val) is not None
            return ok, None if ok else f"{prop}='{val}' does not match /{regex}/"
        if '=' in expr:
            left, right = expr.split('=', 1)
            left = left.strip()
            expected = right.strip()
            if expected.startswith("'") or expected.startswith('"'):
                expected = expected[1:-1]
            _, prop = left.split('.', 1)
            val = obj.get(prop)
            ok = str(val) == expected
            return ok, None if ok else f"Expected {prop}='{expected}', got '{val}'"
    except Exception as e:
        return False, f"DSL evaluation error: {e!s}"
    return False, "Unsupported rule expression"



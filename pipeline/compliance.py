import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from .config_loader import load_yaml_config

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PENALTIES = {
    "critical": 25,
    "major": 10,
    "minor": 3,
}


def _get_by_path(data: Dict[str, Any], path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(str(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def run_compliance(loire: Dict[str, Any], rules_path: str) -> Dict[str, Any]:
    cfg = load_yaml_config(rules_path)
    rules: List[Dict[str, Any]] = cfg.get("rules", [])

    findings: List[Dict[str, Any]] = []
    score = 100

    for rule in rules:
        field = rule.get("field", "")
        severity = rule.get("severity", "minor")
        value = _get_by_path(loire, field)
        violation = False

        if rule.get("rule") == "required":
            if value in (None, "", [], {}):
                violation = True
        elif rule.get("rule") == "format:email":
            if not (isinstance(value, str) and EMAIL_REGEX.match(value or "")):
                violation = True
        elif rule.get("rule") == "format:url":
            if not (isinstance(value, str) and _is_valid_url(value)):
                violation = True

        if violation:
            findings.append({
                "id": rule.get("id"),
                "severity": severity,
                "field": field,
                "message": rule.get("message", ""),
                "rule": rule.get("rule"),
            })
            score -= PENALTIES.get(severity, 0)

    score = max(0, score)
    has_critical_or_major = any(f.get("severity") in {"critical", "major"} for f in findings)
    if has_critical_or_major:
        overall_status = "fail"
    elif findings:
        overall_status = "pass_with_warnings"
    else:
        overall_status = "pass"

    return {
        "overall_status": overall_status,
        "score": score,
        "findings": findings,
    }

import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse


REQUIRED_FIELDS = [
    "datasetTitle",
    "description",
    "publisher.name",
    "contactPoint.email",
    "keywords",
    "license",
    "landingPage",
]

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"\+?\d[\d\-\s]{7,}\d")
LONG_ID_REGEX = re.compile(r"\b\d{10,}\b")
SAFE_PATHS = {
    "issued",
    "contactPoint.email",
    "contact.email",
    "landingPage",
    "license",
    "keywords",
    "datasetTitle",
    "description",
}


class ValidationError(Exception):
    pass


def _get_by_path(data: Dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def detect_pii(data: Any) -> List[str]:
    matches: List[str] = []

    def _scan(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                _scan(v, f"{path}.{k}" if path else k)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                _scan(item, f"{path}[{idx}]")
        elif isinstance(value, str):
            lower = value.lower()
            if any(term in lower for term in ["patient", "dob", "ssn", "social security"]):
                matches.append(path)
            if EMAIL_REGEX.search(value) and path not in {"contactPoint.email", "contact.email"}:
                matches.append(path)
            if PHONE_REGEX.search(value) and path not in SAFE_PATHS:
                matches.append(path)
            if LONG_ID_REGEX.search(value) and path not in SAFE_PATHS:
                matches.append(path)

    _scan(data)
    return matches


def validate_health_dcat(metadata: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], int]:
    errors: List[str] = []

    pii_hits = detect_pii(metadata)
    if pii_hits:
        raise ValidationError(f"PII/PHI indicators found at: {', '.join(pii_hits)}")

    for field in REQUIRED_FIELDS:
        value = _get_by_path(metadata, field)
        if value is None or value == "" or value == []:
            errors.append(f"Missing or empty required field: {field}")

    email = _get_by_path(metadata, "contactPoint.email")
    if email and not EMAIL_REGEX.match(email):
        errors.append("contactPoint.email is not a valid email")

    def _is_valid_url(value: str) -> bool:
        parsed = urlparse(str(value))
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    license_url = metadata.get("license")
    if license_url and not _is_valid_url(str(license_url)):
        errors.append("license must be a valid URL with scheme and host")

    landing = metadata.get("landingPage")
    if landing and not _is_valid_url(str(landing)):
        errors.append("landingPage must be a valid URL with scheme and host")

    quality_score = 100
    quality_score -= 10 * sum(1 for e in errors if "Missing" in e)
    quality_score -= 5 * sum(1 for e in errors if "not a valid" in e)
    quality_score = max(0, min(quality_score, 100))

    return metadata, errors, quality_score

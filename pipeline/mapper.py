import datetime as dt
from typing import Any, Dict, List, Tuple

from .config_loader import load_yaml_config


def _get_by_path(data: Dict[str, Any], path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def map_health_dcat_to_loire(metadata: Dict[str, Any], config_path: str) -> Tuple[Dict[str, Any], List[str], Dict[str, str]]:
    config = load_yaml_config(config_path)

    mappings: Dict[str, str] = config.get("mappings", {})
    required_fields: List[str] = config.get("required_fields", [])
    loire: Dict[str, Any] = {
        "title": None,
        "description": None,
        "publisher": {"name": None},
        "contact": {"email": None, "name": None},
        "keywords": [],
        "license": None,
        "landing_page": None,
        "issued": None,
    }
    provenance: Dict[str, str] = {}
    missing_fields: List[str] = []

    for target, source in mappings.items():
        value = _get_by_path(metadata, source)
        current = loire
        parts = target.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
        provenance[target] = source
        if (value is None or value == "" or value == []) and target in required_fields:
            missing_fields.append(target)

    loire.setdefault("provenance", {})
    loire["provenance"]["mapped_from"] = provenance
    loire["provenance"]["generated_at"] = dt.datetime.utcnow().isoformat() + "Z"
    loire["missing_fields"] = missing_fields

    return loire, missing_fields, provenance

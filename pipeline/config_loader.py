from typing import Any, Dict

def _convert_value(value: str) -> Any:
    value = value.strip()
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    return value


def _manual_parse(path: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    current_section: str | None = None
    current_rule: Dict[str, Any] | None = None

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if line.endswith(":") and not line.strip().startswith("-"):
                current_section = line.strip().rstrip(":")
                if current_section == "rules":
                    result[current_section] = []
                elif current_section not in result:
                    result[current_section] = [] if "required" in current_section else {}
                current_rule = None
                continue

            if current_section == "rules":
                if line.strip().startswith("- "):
                    current_rule = {}
                    result[current_section].append(current_rule)
                    kv = line.strip()[2:]
                    if kv:
                        if ":" in kv:
                            key, val = kv.split(":", 1)
                            current_rule[key.strip()] = _convert_value(val)
                    continue
                if current_rule is not None and ":" in line:
                    key, val = line.strip().split(":", 1)
                    current_rule[key.strip()] = _convert_value(val)
            elif current_section:
                if line.strip().startswith("- "):
                    value = line.strip()[2:]
                    section_value = result.setdefault(current_section, [])
                    if isinstance(section_value, list):
                        section_value.append(_convert_value(value))
                elif ":" in line:
                    key, val = line.strip().split(":", 1)
                    section_value = result.setdefault(current_section, {})
                    if isinstance(section_value, dict):
                        section_value[key.strip()] = _convert_value(val)
    return result


def load_yaml_config(path: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        return _manual_parse(path)



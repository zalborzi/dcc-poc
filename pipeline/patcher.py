from copy import deepcopy
from typing import Any, Dict, List

try:
    import jsonpatch
except ImportError:  # pragma: no cover - optional dependency
    jsonpatch = None  # type: ignore


def _apply_single(target: Dict[str, Any], op: str, path: str, value: Any) -> None:
    pointer = path.lstrip("/")
    parts = pointer.split("/") if pointer else []
    current: Any = target
    for part in parts[:-1]:
        if isinstance(current, list):
            idx = int(part)
            while len(current) <= idx:
                current.append({})
            current = current[idx]
        else:
            current = current.setdefault(part, {})
    if not parts:
        return
    last = parts[-1]
    if isinstance(current, list):
        idx = int(last)
        if op == "add":
            if idx == len(current):
                current.append(value)
            elif 0 <= idx < len(current):
                current.insert(idx, value)
        elif op == "replace" and 0 <= idx < len(current):
            current[idx] = value
    elif isinstance(current, dict):
        current[last] = value


def apply_patches(loire: Dict[str, Any], patches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply JSONPatch operations using jsonpatch when available, with a deterministic fallback."""

    if not patches:
        return loire

    updated = deepcopy(loire)

    if jsonpatch:
        try:
            return jsonpatch.apply_patch(updated, patches, in_place=False)
        except Exception:
            pass

    # Fallback for offline/demo environments or when jsonpatch fails
    try:
        for patch in patches:
            op = patch.get("op")
            path = patch.get("path", "")
            if op not in {"add", "replace"} or not isinstance(path, str):
                continue
            _apply_single(updated, op, path, patch.get("value"))
        return updated
    except Exception:
        return loire

import json
import os
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv() -> bool:  # type: ignore
        return False

DEFAULT_EXPLANATION = {
    "explanation": {"critical": [], "major": [], "minor": []},
    "patches": [],
    "questions": [],
}


def _fallback_patches(loire: Dict[str, Any], findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    patches: List[Dict[str, Any]] = []
    for finding in findings:
        field = finding.get("field")
        rule = finding.get("rule")
        if not field:
            continue
        pointer = "/" + field.replace(".", "/")
        placeholder = "REQUIRED_VALUE"
        if "keywords" in field:
            placeholder = ["REQUIRED_VALUE"]
        elif "email" in field:
            placeholder = "contact@example.com"
        elif "url" in (rule or "") or "landing" in field or "license" in field:
            placeholder = "https://example.com"
        elif "issued" in field:
            placeholder = "2024-01-01"
        patches.append({"op": "add", "path": pointer, "value": placeholder})
    return patches


def _load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _validate_patch_list(patches: Any) -> List[Dict[str, Any]]:
    if not isinstance(patches, list):
        return []
    valid_ops = {"add", "replace"}
    validated: List[Dict[str, Any]] = []
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        op = patch.get("op")
        path = patch.get("path")
        if op in valid_ops and isinstance(path, str) and "value" in patch:
            validated.append({"op": op, "path": path, "value": patch.get("value")})
    return validated


def generate_explanation_and_patches(loire: Dict[str, Any], compliance: Dict[str, Any], required_fields: List[str], prompts_dir: str) -> Dict[str, Any]:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        fallback = DEFAULT_EXPLANATION.copy()
        findings = compliance.get("findings", [])
        fallback["explanation"]["minor"].append(
            "Set OPENAI_API_KEY to enable LLM-based explanations. Deterministic placeholder patches provided."
        )
        fallback["patches"] = _fallback_patches(loire, findings)
        return fallback

    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        fallback = DEFAULT_EXPLANATION.copy()
        fallback["explanation"]["minor"].append(
            "OpenAI client not installed. Install openai or set OPENAI_API_KEY."
        )
        fallback["patches"] = _fallback_patches(loire, compliance.get("findings", []))
        return fallback

    system_prompt = _load_prompt(os.path.join(prompts_dir, "system_prompt.txt"))
    fix_prompt = _load_prompt(os.path.join(prompts_dir, "fix_prompt.txt"))

    client = OpenAI(api_key=api_key, base_url=base_url)

    user_content = {
        "loire": loire,
        "findings": compliance.get("findings", []),
        "required_fields": required_fields,
        "instructions": fix_prompt,
    }

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_content)},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content if response.choices else ""
        parsed = json.loads(content)
    except Exception:
        parsed = DEFAULT_EXPLANATION.copy()
        parsed["explanation"]["minor"].append("Model response invalid or unavailable. No patches applied.")

    explanation = parsed.get("explanation", DEFAULT_EXPLANATION["explanation"])
    patches = _validate_patch_list(parsed.get("patches", []))
    questions = parsed.get("questions", []) if isinstance(parsed.get("questions", []), list) else []

    if not patches and parsed.get("patches"):
        explanation = parsed.get("explanation", explanation)
        explanation.setdefault("minor", []).append("Proposed patches were invalid and were ignored.")

    return {
        "explanation": explanation,
        "patches": patches,
        "questions": questions,
    }

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv() -> bool:  # type: ignore
        return False

from .compliance import run_compliance
from .config_loader import load_yaml_config
from .explain_fix import generate_explanation_and_patches
from .ingest_validate import ValidationError, validate_health_dcat
from .mapper import map_health_dcat_to_loire
from .patcher import apply_patches
from .report import write_reports


load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, os.pardir, "configs")
PROMPTS_DIR = os.path.join(BASE_DIR, os.pardir, "prompts")


def _load_required_fields() -> list:
    data = load_yaml_config(os.path.join(CONFIG_DIR, "loire_required_fields.yaml")) or {}
    return data.get("required", [])


def run_pipeline_stage1(metadata: Dict[str, Any], output_root: Optional[str] = None) -> Dict[str, Any]:
    raw_input = json.dumps(metadata, indent=2)
    output_root = output_root or os.path.join(os.path.dirname(BASE_DIR), "outputs")
    run_id = f"run_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    output_dir = os.path.join(output_root, run_id)

    try:
        validated, validation_errors, quality_score = validate_health_dcat(metadata)
    except ValidationError as exc:  # PII guard triggers
        return {
            "status": "error",
            "error": str(exc),
            "quality_score": 0,
        }

    loire, missing_fields, provenance = map_health_dcat_to_loire(
        validated, os.path.join(CONFIG_DIR, "mapping_healthdcat_to_loire.yaml")
    )

    compliance_before = run_compliance(loire, os.path.join(CONFIG_DIR, "federator_sim_rules.yaml"))

    required_fields = _load_required_fields()
    explain = generate_explanation_and_patches(loire, compliance_before, required_fields, PROMPTS_DIR)
    patches = explain.get("patches", [])

    return {
        "status": "ok",
        "run_id": run_id,
        "output_dir": output_dir,
        "validation_errors": validation_errors,
        "quality_score": quality_score,
        "loire": loire,
        "compliance_before": compliance_before,
        "patches": patches,
        "explanation": explain.get("explanation", {}),
        "questions": explain.get("questions", []),
        "raw_input": raw_input,
    }


def run_pipeline_stage2(stage1_result: Dict[str, Any], output_root: Optional[str] = None) -> Dict[str, Any]:
    if stage1_result.get("status") != "ok":
        return stage1_result

    loire = stage1_result["loire"]
    patches = stage1_result.get("patches", [])
    raw_input = stage1_result.get("raw_input", json.dumps(loire))
    run_id = stage1_result.get("run_id") or f"run_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    output_root = output_root or os.path.join(os.path.dirname(BASE_DIR), "outputs")
    output_dir = stage1_result.get("output_dir") or os.path.join(output_root, run_id)

    loire_after = apply_patches(loire, patches)
    compliance_after = run_compliance(loire_after, os.path.join(CONFIG_DIR, "federator_sim_rules.yaml"))

    try:
        write_reports(
            output_dir,
            {
                "loire_before": loire,
                "loire_after": loire_after,
                "compliance_before": stage1_result["compliance_before"],
                "compliance_after": compliance_after,
                "patches": patches,
            },
            raw_input,
        )
    except OSError:
        pass

    return {
        **stage1_result,
        "run_id": run_id,
        "output_dir": output_dir,
        "loire_after": loire_after,
        "compliance_after": compliance_after,
    }


def run_pipeline(metadata: Dict[str, Any], output_root: Optional[str] = None) -> Dict[str, Any]:
    stage1 = run_pipeline_stage1(metadata, output_root=output_root)
    if stage1.get("status") != "ok":
        return stage1
    return run_pipeline_stage2(stage1, output_root=output_root)

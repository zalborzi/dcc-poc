import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List


def _group_findings(findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {"critical": [], "major": [], "minor": []}
    for finding in findings:
        severity = finding.get("severity", "minor")
        grouped.setdefault(severity, []).append(finding)
    return grouped


def _render_markdown(report: Dict[str, Any], after: bool = False) -> str:
    findings = report.get("findings", [])
    grouped = _group_findings(findings)
    lines = []
    lines.append(f"# Compliance Report {'(After Fixes)' if after else '(Before Fixes)'}")
    lines.append("")
    lines.append(f"**Status:** {report.get('overall_status')}  ")
    lines.append(f"**Score:** {report.get('score')}")
    lines.append("")
    for severity in ["critical", "major", "minor"]:
        lines.append(f"## {severity.title()} Findings")
        if not grouped.get(severity):
            lines.append("- None")
        else:
            for finding in grouped[severity]:
                lines.append(f"- [{finding.get('id')}] {finding.get('field')}: {finding.get('message')}")
        lines.append("")
    return "\n".join(lines)


def write_reports(output_dir: str, run_artifacts: Dict[str, Any], raw_input: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    checksum = hashlib.sha256(raw_input.encode("utf-8")).hexdigest()
    audit = {
        "run_id": os.path.basename(output_dir),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "input_checksum": checksum,
    }

    before_loire = run_artifacts["loire_before"]
    after_loire = run_artifacts.get("loire_after", before_loire)

    with open(os.path.join(output_dir, "loire_self_description.json"), "w", encoding="utf-8") as f:
        json.dump(before_loire, f, indent=2)
    with open(os.path.join(output_dir, "loire_self_description_after.json"), "w", encoding="utf-8") as f:
        json.dump(after_loire, f, indent=2)

    with open(os.path.join(output_dir, "fix_patches.json"), "w", encoding="utf-8") as f:
        json.dump(run_artifacts.get("patches", []), f, indent=2)

    before_report = run_artifacts["compliance_before"]
    after_report = run_artifacts["compliance_after"]

    with open(os.path.join(output_dir, "compliance_report.json"), "w", encoding="utf-8") as f:
        json.dump(before_report, f, indent=2)
    with open(os.path.join(output_dir, "compliance_report_after.json"), "w", encoding="utf-8") as f:
        json.dump(after_report, f, indent=2)

    md_before = _render_markdown(before_report)
    md_after = _render_markdown(after_report, after=True)

    delta_score = after_report.get("score", 0) - before_report.get("score", 0)
    resolved = len(before_report.get("findings", [])) - len(after_report.get("findings", []))

    summary_lines = [
        "# Executive Summary",
        f"- Score Before: {before_report.get('score')} ({before_report.get('overall_status')})",
        f"- Score After: {after_report.get('score')} ({after_report.get('overall_status')})",
        f"- Score Delta: {delta_score}",
        f"- Findings Resolved: {resolved}",
        "",
        "## Suggested Patches",
        "```json",
        json.dumps(run_artifacts.get("patches", []), indent=2),
        "```",
        "",
        "## Audit",
        f"- Run ID: {audit['run_id']}",
        f"- Generated At: {audit['generated_at']}",
        f"- Input SHA256: {audit['input_checksum']}",
        "",
        "---",
        md_before,
        "---",
        md_after,
    ]

    with open(os.path.join(output_dir, "compliance_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    with open(os.path.join(output_dir, "compliance_report_after.md"), "w", encoding="utf-8") as f:
        f.write(md_after)

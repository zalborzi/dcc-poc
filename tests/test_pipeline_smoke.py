import json
from pathlib import Path

from pipeline import run_pipeline


def load_sample(name: str) -> dict:
    sample_path = Path(__file__).parents[1] / "samples" / name
    return json.loads(sample_path.read_text())


def test_pipeline_end_to_end(tmp_path):
    good = load_sample("good_health_dcat.json")
    bad = load_sample("bad_health_dcat_missing_fields.json")

    good_result = run_pipeline(good, output_root=str(tmp_path))
    bad_result = run_pipeline(bad, output_root=str(tmp_path))

    assert good_result["status"] == "ok"
    assert bad_result["status"] == "ok"

    good_score_before = good_result["compliance_before"]["score"]
    bad_score_before = bad_result["compliance_before"]["score"]
    assert good_score_before > bad_score_before

    after_score = bad_result["compliance_after"]["score"]
    after_findings = bad_result["compliance_after"].get("findings", [])
    before_findings = bad_result["compliance_before"].get("findings", [])

    critical_before = [f for f in before_findings if f.get("severity") == "critical"]
    critical_after = [f for f in after_findings if f.get("severity") == "critical"]

    assert after_score >= bad_score_before or len(critical_after) < len(critical_before)

    output_dir = Path(bad_result["output_dir"])
    expected_files = {
        "loire_self_description.json",
        "compliance_report.json",
        "compliance_report.md",
        "fix_patches.json",
        "loire_self_description_after.json",
        "compliance_report_after.json",
        "compliance_report_after.md",
    }
    assert expected_files.issubset({p.name for p in output_dir.iterdir()})

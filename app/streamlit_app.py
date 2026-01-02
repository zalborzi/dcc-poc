import json
import os
from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv() -> bool:  # type: ignore
        return False

from pipeline import run_pipeline_stage1, run_pipeline_stage2

load_dotenv()

st.set_page_config(page_title="Dataspace Compliance Copilot", layout="wide")


def load_report_md(output_dir: str) -> str:
    report_path = Path(output_dir) / "compliance_report.md"
    if report_path.exists():
        return report_path.read_text(encoding="utf-8")
    return "Report not available."


def render_compliance(title: str, report: dict):
    st.subheader(title)
    st.write(f"Status: **{report.get('overall_status')}** | Score: **{report.get('score')}**")
    if report.get("findings"):
        for finding in report["findings"]:
            st.write(f"- [{finding.get('severity')}] {finding.get('field')}: {finding.get('message')}")
    else:
        st.success("No findings")


def main():
    st.title("Dataspace Compliance Copilot (DCC)")
    st.write("Upload Health DCAT-AP metadata JSON to validate, map, and check compliance.")

    uploaded = st.file_uploader("Upload Health DCAT-AP JSON", type=["json"])

    if uploaded:
        try:
            metadata = json.load(uploaded)
            st.session_state["metadata"] = metadata
            st.session_state.pop("stage1", None)
            st.session_state.pop("result_after", None)
        except json.JSONDecodeError:
            st.error("Invalid JSON file. Please upload a valid Health DCAT-AP JSON.")
            return

    if "metadata" in st.session_state:
        st.json(st.session_state["metadata"], expanded=False)
        if st.button("Run compliance and suggest fixes (no apply yet)"):
            with st.spinner("Running analysis..."):
                stage1 = run_pipeline_stage1(st.session_state["metadata"])
                st.session_state["stage1"] = stage1
                st.session_state.pop("result_after", None)

    stage1 = st.session_state.get("stage1")
    if stage1:
        if stage1.get("status") != "ok":
            st.error(stage1.get("error", "Unknown error"))
            return

        st.write(f"Validation quality score: **{stage1.get('quality_score')}**")
        if stage1.get("validation_errors"):
            st.warning("Validation warnings:")
            for err in stage1["validation_errors"]:
                st.write(f"- {err}")

        st.subheader("Loire Self-Description (Before Patches)")
        st.json(stage1.get("loire", {}), expanded=False)

        render_compliance("Compliance - Before", stage1.get("compliance_before", {}))

        st.subheader("Suggested Explanation and Patches")
        st.json({
            "explanation": stage1.get("explanation"),
            "patches": stage1.get("patches"),
            "questions": stage1.get("questions"),
        }, expanded=False)

        if st.button("Apply suggested fixes and re-run", type="primary"):
            with st.spinner("Applying patches and re-running..."):
                stage2 = run_pipeline_stage2(stage1)
                st.session_state["result_after"] = stage2

    result_after = st.session_state.get("result_after")
    if result_after:
        st.subheader("Loire Self-Description (After Patches)")
        st.json(result_after.get("loire_after", {}), expanded=False)

        render_compliance("Compliance - After", result_after.get("compliance_after", {}))

        if result_after.get("output_dir") and os.path.exists(result_after.get("output_dir")):
            st.subheader("Markdown Report")
            st.markdown(load_report_md(result_after["output_dir"]))
        else:
            st.info("Report not available; ensure application can write to outputs directory.")


if __name__ == "__main__":
    main()

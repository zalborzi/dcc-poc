# Dataspace Compliance Copilot (DCC)

Dataspace Compliance Copilot (DCC) is a proof-of-concept that ingests Health DCAT-AP metadata, validates and maps it into a Gaia-X Loire-like self-description, simulates a Federator/GXDCH compliance check, asks an LLM for explanations and JSONPatch fixes (with deterministic fallbacks), applies patches, and generates before/after reports. A Streamlit UI demonstrates the closed loop.

## Features
- Input validation with quality scoring and PII/PHI heuristics (metadata-only; no PHI allowed).
- Config-driven mapping from Health DCAT-AP to Loire self-description with provenance capture.
- Deterministic compliance simulation using local rules and severity penalties.
- LLM-based explanations and patch suggestions (OpenAI API), with deterministic placeholder patches when no API key is set.
- JSONPatch application, re-check loop, and Markdown/JSON reporting with audit data.
- Streamlit UI for interactive demos.

## Setup
1. Python 3.11 is required.
2. Create and activate a virtual environment.
3. Install dependencies:
   ```bash
   pip install -e .
   ```
4. Copy the environment template and set your OpenAI credentials (optional for deterministic fallback patches):
   ```bash
   cp .env.example .env
   # edit .env to set OPENAI_API_KEY and OPENAI_MODEL
   ```

## Running the Streamlit app
```bash
streamlit run app/streamlit_app.py
```
Upload one of the sample metadata files from `samples/` to see the validation and compliance loop. `.env` is automatically loaded; if no `OPENAI_API_KEY` is provided, deterministic placeholder patches will be used.

## Running tests
```bash
pytest
```

## Demo steps
1. Run the Streamlit app.
2. Upload `samples/bad_health_dcat_missing_fields.json` to see validation errors, compliance findings, and suggested patches (before applying).
3. Click **Apply suggested fixes and re-run** to observe improved compliance scores and updated reports.
4. Use `samples/good_health_dcat.json` to observe a passing run.

## Notes
- No external connectivity is required beyond the optional LLM call.
- The system operates on metadata only; inputs containing PII/PHI indicators are rejected.
- Outputs are written to `outputs/run_<timestamp>/` and include JSON and Markdown reports for auditing.

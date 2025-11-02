# llm/assist.py
import json
from llm.bedrock_integration import generate_narrative

# --- simple wrappers so Streamlit can call them cleanly ---
def build_summary(report_json):
    findings = report_json.get("rows", [])
    narrative = generate_narrative(findings, prompt_file="prompts/summary_v1.md")
    class Summary:
        executive_summary = narrative
        log_uri = None
    return Summary()

def explain_control(report_json, control_id):
    findings = [r for r in report_json.get("rows", []) if r.get("control_id") == control_id]
    narrative = generate_narrative(findings, prompt_file="prompts/rationale_v1.md")
    class Rationale:
        rationale = narrative.splitlines()
        log_uri = None
    return Rationale()

def fuzzy_hint(report_json, control_id):
    findings = [r for r in report_json.get("rows", []) if r.get("control_id") == control_id]
    return generate_narrative(findings, prompt_file="prompts/fuzzy_hint_v1.md")


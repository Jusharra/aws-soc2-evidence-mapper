# llm/bedrock_integration.py
import os, json, re, time, random, boto3, botocore

# --- Basic Config ---
REGION       = os.getenv("AWS_REGION", "us-east-1")
MODEL_ID     = os.getenv("OPENAI_MODEL_ID", "amazon.nova-lite-v1:0")
TEMP         = float(os.getenv("LLM_TEMPERATURE", "0.2"))
MAX_TOKENS   = int(os.getenv("LLM_MAX_TOKENS", "800"))
TIMEOUT_SECS = int(os.getenv("LLM_TIMEOUT_SECS", "18"))

# --- Bedrock client ---
_brt = boto3.client(
    "bedrock-runtime",
    region_name=REGION,
    config=botocore.config.Config(
        read_timeout=TIMEOUT_SECS,
        connect_timeout=5,
        retries={"max_attempts": 2, "mode": "standard"},
    ),
)

# --- Simple redaction helpers (no inline regex flags) ---
EMAIL     = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
UUID_LIKE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.IGNORECASE)
SECRET_K  = re.compile(r"\b(api|client|db|token|secret|key|password)\b", re.IGNORECASE)

def _scrub_text(s: str) -> str:
    s = EMAIL.sub("[REDACTED_EMAIL]", s)
    s = UUID_LIKE.sub("[REDACTED_UUID]", s)
    s = SECRET_K.sub("[REDACTED_SECRET]", s)
    return s

def _scrub_json(d: dict) -> str:
    return _scrub_text(json.dumps(d, ensure_ascii=False))

# --- Retry helper ---
def _retry(fn, attempts=3, base=0.4, cap=4.0):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(min(cap, base * (2 ** i)) * (0.5 + random.random()))
    raise last

# --- Prompt builder (concise) ---
def prepare_prompt(findings: list[dict]) -> str:
    severities = ["Critical", "High", "Medium", "Low", "Informational"]
    counts = {s: 0 for s in severities}
    cats = {}
    for f in findings or []:
        s = f.get("severity")
        if s in counts:
            counts[s] += 1
        c = f.get("category", "Other")
        cats.setdefault(c, []).append(f)

    lines = []
    for c, group in cats.items():
        lines.append(f"\nCategory: {c}")
        order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Informational": 4}
        for f in sorted(group, key=lambda x: order.get(x.get("severity", "Low"), 99))[:5]:
            lines.append(f"  - {f.get('severity')}: {f.get('description')} ({f.get('resource_type')}:{f.get('resource_id')})")
        if len(group) > 5:
            lines.append(f"  - ... and {len(group)-5} more {c} findings")

    return f"""<findings>
# AWS Security Findings Summary

Total findings: {sum(counts.values())}
- Critical: {counts['Critical']}
- High: {counts['High']}
- Medium: {counts['Medium']}
- Low: {counts['Low']}
- Informational: {counts['Informational']}

## Findings by Category:
{chr(10).join(lines)}
</findings>"""

# --- Model invocation ---
def _invoke_model(prompt_text: str) -> str:
    """Send prompt to Nova (messages API) or default fallback body."""
    mid = MODEL_ID

    # Prefer Nova message schema if using an amazon.nova-* model
    if mid.startswith("amazon.nova-"):
        body = {
            "messages": [
                {"role": "user", "content": [{"text": (
                    "You are a cybersecurity auditor assistant. "
                    "Write a concise executive summary with top risks and recommendations "
                    "from the following findings (≤180 words; redact PII).\n\n" + prompt_text
                )}]}
            ],
            "inferenceConfig": {
                "maxTokens": MAX_TOKENS,
                "temperature": TEMP,
                "topP": 0.9
            }
        }
    else:
        # Generic (Claude-style) fallback
        body = {
            "prompt": (
                "\n\nHuman: Analyze these AWS security findings and write an executive summary "
                "with critical risks and recommendations.\n\n"
                f"{prompt_text}\n\nAssistant:"
            ),
            "max_tokens_to_sample": MAX_TOKENS,
            "temperature": TEMP,
        }

    def _do():
        resp = _brt.invoke_model(
            modelId=mid,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body).encode("utf-8"),
        )
        return resp["body"].read().decode("utf-8")

    return _retry(_do)


# --- Narrative helpers ---
def extract_narrative(raw_text: str) -> str:
    """
    Parse common Bedrock responses:
    - Nova: {"output":{"message":{"content":[{"text":"..."}]}}}
    - Claude/others: {"completion": "..."} or {"outputText": "..."}
    """
    try:
        data = json.loads(raw_text)
    except Exception:
        return raw_text.strip()

    # Direct fields first
    for key in ("completion", "outputText", "generation", "answer", "output"):
        if key in data and isinstance(data[key], str):
            return data[key].strip()

    # Nova nested shape
    try:
        msg = data.get("output", {}).get("message", {})
        parts = msg.get("content", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
        if texts:
            return " ".join(t.strip() for t in texts if t).strip()
    except Exception:
        pass

    # Some providers return an array of outputs
    try:
        outs = data.get("outputs", [])
        if outs and isinstance(outs, list):
            parts = outs[0].get("content", [])
            texts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
            if texts:
                return " ".join(t.strip() for t in texts if t).strip()
    except Exception:
        pass

    return str(data).strip()

def generate_fallback_narrative() -> str:
    return (
        "# AWS Security Narrative (Fallback)\n\n"
        "AI narrative unavailable. Review deterministic mapping report.\n\n"
        "Next steps:\n"
        "- Prioritize Critical/High findings.\n"
        "- Validate timestamps; remediate drift.\n"
        "- Re-run assessment after remediation.\n"
    )

# --- Public entrypoints ---
def generate_narrative(findings: list[dict], prompt_file: str = "prompts/summary_v1.md") -> str:
    """
    Use an external prompt file (from the prompts/ directory) to guide the model.
    Falls back gracefully if Bedrock fails.
    """
    try:
        # Load your existing prompt template from /prompts/
        if os.path.exists(prompt_file):
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        else:
            prompt_template = (
                "You are an AI auditor assistant. Summarize and explain findings clearly."
            )

        # Build the AI-ready message using your external template + data
        prompt_body = f"{prompt_template}\n\nJSON:\n{json.dumps(findings, indent=2)}"

        # Redact PII or secrets before sending
        safe_prompt = _scrub_text(prompt_body)

        # Invoke Bedrock model and extract narrative
        raw = _invoke_model(safe_prompt)
        narrative = extract_narrative(raw).strip()

        # If model gave no output, fallback
        if not narrative:
            narrative = generate_fallback_narrative()
        return narrative

    except Exception as e:
        print(f"[AI error] {e}")
        return generate_fallback_narrative()


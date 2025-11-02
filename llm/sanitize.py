# llm/sanitize.py
import json, re

EMAIL     = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
UUID_LIKE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[089ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.IGNORECASE)
SECRET_K  = re.compile(r"\b(api|client|db|token|secret|key|password|bearer|access[-_ ]?key)\b", re.IGNORECASE)
PII_WORDS = re.compile(r"\b(ssn|sin|passport|driver'?s?\s*license|dob|date of birth)\b", re.IGNORECASE)

def scrub_text(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = EMAIL.sub("[REDACTED_EMAIL]", s)
    s = UUID_LIKE.sub("[REDACTED_UUID]", s)
    s = SECRET_K.sub("[REDACTED_SECRET]", s)
    s = PII_WORDS.sub("[REDACTED_PII]", s)
    return s

def scrub_json(d: dict) -> str:
    """Serialize and scrub a JSON-safe dict."""
    s = json.dumps(d, ensure_ascii=False)
    return scrub_text(s)

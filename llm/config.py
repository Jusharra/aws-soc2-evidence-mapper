from __future__ import annotations
import os

class LlmConfig:
    region: str
    model_id: str
    temperature: float
    max_tokens: int
    s3_bucket: str
    redact: bool
    timeout_secs: int

    def __init__(self) -> None:
        self.region       = os.getenv("AWS_REGION", "us-east-1")
        self.model_id     = os.getenv("OPENAI_MODEL_ID", "amazon.nova-lite-v1:0")  # put your working ID here
        self.temperature  = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens   = int(os.getenv("LLM_MAX_TOKENS", "800"))
        self.s3_bucket    = os.getenv("DATA_BUCKET", "")
        self.redact       = os.getenv("LLM_REDACT", "true").lower() == "true"
        self.timeout_secs = int(os.getenv("LLM_TIMEOUT_SECS", "18"))  # keep low for UI

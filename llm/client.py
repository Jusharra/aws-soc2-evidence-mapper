from __future__ import annotations
import json, boto3, botocore
from typing import Dict, Any
from .config import LlmConfig
from .retry import retry

_cfg = LlmConfig()

# Create client with low timeouts so UI doesn’t hang
_session = boto3.session.Session(region_name=_cfg.region)
_brt = _session.client(
    "bedrock-runtime",
    config=botocore.config.Config(
        read_timeout=_cfg.timeout_secs,
        connect_timeout=5,
        retries={"max_attempts": 2, "mode": "standard"},
    ),
)

def invoke_llm_text(input_text: str, *, temperature: float | None = None,
                    max_tokens: int | None = None) -> str:
    body: Dict[str, Any] = {
        "inputText": input_text,
        "temperature": temperature if temperature is not None else _cfg.temperature,
        "maxTokens": max_tokens if max_tokens is not None else _cfg.max_tokens,
    }

    def _call() -> str:
        resp = _brt.invoke_model(
            modelId=_cfg.model_id,
            body=json.dumps(body).encode("utf-8"),
            contentType="application/json",
            accept="application/json",
        )
        return resp["body"].read().decode("utf-8")

    try:
        return retry(_call, attempts=4)
    except Exception as e:
        raise RuntimeError(f"Bedrock model invoke failed: {e}")

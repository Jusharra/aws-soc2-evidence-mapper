from __future__ import annotations
import os, json, uuid, datetime as dt, boto3
from typing import Literal, Optional

_s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION","us-east-1"))
_BUCKET = os.getenv("DATA_BUCKET","")

def log_llm_event(kind: Literal["summary","rationale","fuzzy"], prompt: str, output: str,
                  *, prefix: str = "llm_logs/") -> Optional[str]:
    if not _BUCKET:
        return None
    rid = uuid.uuid4().hex[:8]
    key = f"{prefix}{dt.datetime.utcnow():%Y%m%d}/{kind}-{rid}.json"
    body = {
        "ts": f"{dt.datetime.utcnow().isoformat()}Z",
        "kind": kind,
        "prompt_len": len(prompt),
        "output_len": len(output),
        "prompt": prompt,
        "output": output,
    }
    _s3.put_object(Bucket=_BUCKET, Key=key, Body=json.dumps(body).encode("utf-8"))
    return f"s3://{_BUCKET}/{key}"

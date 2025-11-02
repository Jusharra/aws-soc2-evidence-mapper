from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class LlmSummary:
    executive_summary: str
    table_md: str
    next_action: str
    log_uri: Optional[str] = None

@dataclass
class LlmRationale:
    control_id: str
    rationale: List[str]
    cited_fields: List[str]
    gaps: List[str]
    log_uri: Optional[str] = None

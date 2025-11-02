# SOC 2 Auditor AI Agent — Design & Mapping Logic

**What:** Prototype to automate mapping of evidence to SOC 2 controls and flag compliance drift.  
**How:** Deterministic keyword matching + (optional) LLM rationale; Lambda writes JSON report to S3.  
**Why (for CISOs & Auditors):** Reduce audit toil, standardize evidence, and surface freshness gaps.

**Mapping Heuristic (MVP):**
1. Tokenize control keywords (owner-tunable).
2. If a piece of evidence contains ≥1 keyword → candidate link.
3. Compute drift by comparing `last_updated` to control `max_evidence_age_days`.
4. Summarize per control: PASS (at least one non-drift), PARTIAL (some non-drift + some drift), FAIL (only drift or no evidence).

**Controls Covered (sample):** CC1.1, CC6.1, CC6.6, CC7.2, CC8.1.

**Risk Considerations:**
- False positives/negatives on keyword logic (mitigate with LLM + feedback).
- Staleness of evidence (enforce SLAs, alerts).
- Access control on evidence S3 bucket (SSE, least privilege).

**Roadmap:**
- Swap deterministic matcher for embedding search (Pinecone).
- Pull live data from Security Hub, Audit Manager, AWS Config.
- Add MCP/Amazon Q Agent endpoint for auditor Q&A.

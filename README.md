# AWS SOC 2 Evidence Collection + Auditor AI Agent (Lab)

**Timebox:** ~1–2 hours  
**Goal:** Prototype an AI workflow that automates SOC 2 evidence collection, mapping, and reporting with drift detection.

## Architecture (MVP)
- **S3**: controls.csv, evidence.csv, reports/latest_report.json
- **Lambda (Python)**: deterministic keyword mapper + drift detection
- **(Optional) Bedrock**: LLM assist for fuzzy mapping/explanations
- **CloudFormation**: S3, IAM role, Lambda shell
- **Streamlit**: local demo UI for the “Auditor AI Agent”

## Quickstart
1. Create the S3 bucket and Lambda via CloudFormation:
   ```bash
   aws cloudformation deploy --template-file infra/template.yaml --stack-name soc2-agent --parameter-overrides DataBucketName=<your-unique-bucket> --capabilities CAPABILITY_NAMED_IAM
   ```
2. Upload sample data:
   ```bash
   aws s3 cp data/controls.csv s3://<your-unique-bucket>/data/controls.csv
   aws s3 cp data/evidence.csv s3://<your-unique-bucket>/data/evidence.csv
   ```
3. Package and update the Lambda code:
   ```bash
   cd lambda && zip function.zip evidence_mapper.py && cd -
   aws lambda update-function-code --function-name soc2-evidence-mapper --zip-file fileb://lambda/function.zip
   ```
4. Run the mapper:
   ```bash
   aws lambda invoke --function-name soc2-evidence-mapper /dev/stdout
   aws s3 cp s3://<your-unique-bucket>/reports/latest_report.json ./reports/latest_report.json
   ```
5. Local demo UI:
   ```bash
   pip install streamlit pandas
   streamlit run app/streamlit_app.py
   ```
6. (Optional) Plug in Bedrock in Lambda for fuzzy matching and natural language rationales.

## Compliance Drift
Evidence older than `max_evidence_age_days` on a control is flagged as **drift**. Defaults included in `data/controls.csv`.

## Sample Data
- `data/controls.csv`: small subset of SOC 2 (Security, Availability) controls with keywords.
- `data/evidence.csv`: mixed sources (Security Hub, AWS Config, Jira, CloudWatch, CodeRepo).
- `data/config_logs.json` and `data/jira_issues.json`: simulated multi-source inputs.

## Reporting
- `reports/latest_report.json`: produced by Lambda (includes PASS/PARTIAL/FAIL per control).

## Next Steps
- Add ingestion from **Security Hub**, **Audit Manager**, **AWS Config** APIs
- Persist mappings in **Pinecone** (vector search) for similarity-based evidence discovery
- Add **Amazon Q / MCP server** to expose an Agent API for auditors

---

© 2025 Demo Lab

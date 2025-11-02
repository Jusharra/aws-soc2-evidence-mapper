import os, csv, io, json, datetime, re
from collections import defaultdict

DRIFT_DAYS_DEFAULT = 30

def parse_keywords(s):
    return [k.strip().lower() for k in s.split(";") if k.strip()]

def load_csv_from_s3(s3_client, bucket, key):
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read().decode("utf-8")
    buf = io.StringIO(data)
    reader = csv.DictReader(buf)
    return list(reader)

def map_evidence(controls, evidence):
    mappings = []
    today = datetime.date.today()
    for c in controls:
        c_keywords = parse_keywords(c.get("keywords",""))
        max_age = int(c.get("max_evidence_age_days") or DRIFT_DAYS_DEFAULT)
        for e in evidence:
            text = (e.get("description","") + " " + e.get("source","")).lower()
            score = sum(1 for kw in c_keywords if kw in text)
            if score>0:
                last = datetime.date.fromisoformat(e["last_updated"][:10])
                age_days = (today - last).days
                compliant = age_days <= max_age
                mappings.append({
                    "control_id": c["control_id"],
                    "control_name": c["control_name"],
                    "trust_service": c["trust_service"],
                    "evidence_id": e["evidence_id"],
                    "evidence_source": e["source"],
                    "evidence_desc": e["description"],
                    "last_updated": e["last_updated"],
                    "age_days": age_days,
                    "max_age_days": max_age,
                    "drift": not compliant,
                    "match_score": score
                })
    return mappings

def summarize(mappings):
    from collections import defaultdict
    by_control = defaultdict(lambda: {"total":0,"ok":0,"drift":0,"evidence":[]})
    for m in mappings:
        d = by_control[m["control_id"]]
        d["total"] += 1
        if m["drift"]:
            d["drift"] += 1
        else:
            d["ok"] += 1
        d["evidence"].append(m)
    summary = []
    for cid, stats in by_control.items():
        status = "PASS" if stats["ok"]>0 and stats["drift"]==0 else ("PARTIAL" if stats["ok"]>0 else "FAIL")
        summary.append({
            "control_id": cid,
            "status": status,
            "ok_evidence": stats["ok"],
            "drift_evidence": stats["drift"],
            "total_evidence": stats["total"],
            "evidence": stats["evidence"]
        })
    return summary

def handler(event, context):
    import boto3
    s3 = boto3.client("s3")
    bucket = os.environ["DATA_BUCKET"]
    controls_key = os.environ.get("CONTROLS_KEY","data/controls.csv")
    evidence_key = os.environ.get("EVIDENCE_KEY","data/evidence.csv")
    output_key = os.environ.get("OUTPUT_KEY","reports/latest_report.json")

    controls = load_csv_from_s3(s3, bucket, controls_key)
    evidence = load_csv_from_s3(s3, bucket, evidence_key)

    mappings = map_evidence(controls, evidence)
    report = {
        "generated_at": datetime.datetime.utcnow().isoformat()+"Z",
        "policy": "SOC 2 (Security, Availability) — demo subset",
        "summary": summarize(mappings)
    }
    s3.put_object(Bucket=bucket, Key=output_key, Body=json.dumps(report, indent=2).encode("utf-8"))
    return {"status":"ok","output_s3": f"s3://{bucket}/{output_key}","counts": len(mappings)}

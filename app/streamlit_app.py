import streamlit as st
import pandas as pd
import json, datetime

st.set_page_config(page_title="SOC 2 Evidence Mapper (Deterministic)", layout="wide")
st.title("SOC 2 Evidence Collection • Deterministic Mapping Demo")

st.markdown("""
Upload **controls.csv** and **evidence.csv**.
The demo maps evidence to SOC 2 controls using simple keyword matching
and flags **drift** when evidence is older than `max_evidence_age_days`.
""")

controls_file = st.file_uploader("Upload controls.csv", type=["csv"])
evidence_file = st.file_uploader("Upload evidence.csv", type=["csv"])

def parse_keywords(s):
    return [k.strip().lower() for k in str(s or "").split(";") if k and k.strip()]

def map_evidence(controls, evidence):
    rows = []
    today = datetime.date.today()
    for _, c in controls.iterrows():
        c_kw = parse_keywords(c.get("keywords", ""))
        max_age = int(c.get("max_evidence_age_days", 30) or 30)
        for _, e in evidence.iterrows():
            text = (str(e.get("description","")) + " " + str(e.get("source",""))).lower()
            score = sum(1 for kw in c_kw if kw in text)
            if score > 0:
                last = datetime.date.fromisoformat(str(e["last_updated"])[:10])
                age_days = (today - last).days
                compliant = age_days <= max_age
                rows.append({
                    "control_id": c["control_id"],
                    "control_name": c.get("control_name",""),
                    "trust_service": c.get("trust_service",""),
                    "evidence_id": e["evidence_id"],
                    "source": e.get("source",""),
                    "desc": e.get("description",""),
                    "last_updated": e["last_updated"],
                    "age_days": age_days,
                    "max_age_days": max_age,
                    "drift": not compliant,
                    "match_score": score
                })
    return pd.DataFrame(rows)

col1, col2 = st.columns(2)
if controls_file:
    controls_df = pd.read_csv(controls_file)
    with col1:
        st.subheader("Controls")
        st.dataframe(controls_df, use_container_width=True)
if evidence_file:
    evidence_df = pd.read_csv(evidence_file)
    with col2:
        st.subheader("Evidence")
        st.dataframe(evidence_df, use_container_width=True)

if controls_file and evidence_file:
    df = map_evidence(controls_df, evidence_df)
    st.subheader("Mappings")
    st.dataframe(df, use_container_width=True)

    st.subheader("Per-control Summary")
    summary = df.groupby("control_id", as_index=False).apply(
        lambda x: pd.Series({
            "ok_evidence": (x["drift"]==False).sum(),
            "drift_evidence": (x["drift"]==True).sum(),
            "total_evidence": len(x),
            "status": (
                "PASS" if ((x["drift"]==False).sum()>0 and (x["drift"]==True).sum()==0)
                else ("PARTIAL" if (x["drift"]==False).sum()>0 else "FAIL")
            )
        })
    ).reset_index(drop=True)
    st.dataframe(summary, use_container_width=True)

    # Deterministic report JSON (what you can hand to auditors)
    report_json = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": summary.to_dict(orient="records"),
        "rows": df[[
            "control_id","control_name","trust_service","evidence_id",
            "source","desc","last_updated","age_days","max_age_days","drift","match_score"
        ]].to_dict(orient="records")
    }

    st.download_button("Download report.json",
        data=json.dumps(report_json, indent=2),
        file_name="report.json",
        mime="application/json")
else:
    st.info("Upload both CSVs to generate mappings.")

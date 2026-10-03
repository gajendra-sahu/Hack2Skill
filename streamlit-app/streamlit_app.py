import os
import re
import json
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="RegIntel 360", page_icon="🛡️", layout="wide")

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))

SYSTEM_PROMPT = """You are RegIntel 360, a fraud and risk intelligence analyst.
You answer questions about these Snowflake tables in REGINTEL360.RISK:

TRANSACTIONS (alias: t) columns: TRANSACTION_ID, CUSTOMER_ID, TRANSACTION_TS (timestamp),
  COUNTRY, CURRENCY, AMOUNT, CHANNEL (ONLINE/MOBILE/API/BRANCH),
  MERCHANT_CATEGORY, PAYMENT_METHOD, LABEL (NORMAL/STRUCTURING/RAPID_VELOCITY/HIGH_RISK_MERCHANT)

RISK_ALERTS (alias: a) columns: ALERT_ID, TRANSACTION_ID, CUSTOMER_ID,
  PATTERN (STRUCTURING/RAPID_VELOCITY/HIGH_RISK_MERCHANT), RISK_SCORE (0-100), REASON, CREATED_AT

REGULATORY_DOCUMENTS (alias: d) columns: DOCUMENT_ID, TITLE, DOMAIN, AUTHORITY, EFFECTIVE_DATE, CONTENT

FEED_HISTORY columns: FEED_ID, FEED_SOURCE, TABLE_NAME, FILE_NAME, ROWS_LOADED, STATUS, ERROR_MESSAGE, LOADED_AT, LOADED_BY

SQL Rules (MANDATORY):
- Write exactly ONE Snowflake SQL query inside ```sql ... ``` fences.
- ALWAYS use fully qualified table names: REGINTEL360.RISK.TRANSACTIONS, REGINTEL360.RISK.RISK_ALERTS, etc.
- When using aliases, define them in the FROM clause: FROM REGINTEL360.RISK.TRANSACTIONS t
- When joining: FROM REGINTEL360.RISK.TRANSACTIONS t JOIN REGINTEL360.RISK.RISK_ALERTS a ON t.TRANSACTION_ID = a.TRANSACTION_ID
- NEVER use bare table names like TRANSACTIONS or RISK_ALERTS without the REGINTEL360.RISK. prefix.
- After the SQL, give a brief plain-language explanation.
- All data is synthetic. Say so if the user asks about real compliance."""


def cortex_complete(prompt_messages):
    """Call Cortex COMPLETE via SQL with the multi-message signature."""
    # Build a single prompt string from the message list
    prompt_parts = []
    for msg in prompt_messages:
        role = msg["role"].upper()
        prompt_parts.append(f"[{role}]\n{msg['content']}")
    prompt_text = "\n\n".join(prompt_parts) + "\n\n[ASSISTANT]\n"

    session = conn.session()
    result = session.sql(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS response",
        params=["llama3.3-70b", prompt_text],
    ).collect()
    return result[0]["RESPONSE"]


# ═══════════════════════ CACHED LOADERS ═══════════════════════
@st.cache_data(ttl=300)
def load_kpis():
    return conn.query("""
        SELECT
            (SELECT COUNT(*) FROM REGINTEL360.RISK.TRANSACTIONS)                       AS txn_count,
            (SELECT COUNT(*) FROM REGINTEL360.RISK.RISK_ALERTS)                        AS alert_count,
            (SELECT COUNT(*) FROM REGINTEL360.RISK.REGULATORY_DOCUMENTS)               AS doc_count,
            (SELECT COUNT(*) FROM REGINTEL360.RISK.RISK_ALERTS WHERE RISK_SCORE >= 60) AS high_risk,
            (SELECT ROUND(COUNT_IF(LABEL<>'NORMAL')/COUNT(*)*100,1)
             FROM REGINTEL360.RISK.TRANSACTIONS)                                       AS fraud_rate
    """)


@st.cache_data(ttl=300)
def load_label_breakdown():
    return conn.query("""
        SELECT LABEL, COUNT(*) AS TRANSACTIONS, SUM(AMOUNT) AS TOTAL_AMOUNT
        FROM REGINTEL360.RISK.TRANSACTIONS GROUP BY LABEL ORDER BY TRANSACTIONS DESC
    """)


@st.cache_data(ttl=300)
def load_pattern_distribution():
    return conn.query("""
        SELECT PATTERN, COUNT(*) AS ALERTS, ROUND(AVG(RISK_SCORE),1) AS AVG_SCORE
        FROM REGINTEL360.RISK.RISK_ALERTS GROUP BY PATTERN ORDER BY ALERTS DESC
    """)


@st.cache_data(ttl=300)
def load_country_breakdown():
    return conn.query("""
        SELECT COUNTRY, COUNT(*) AS TRANSACTIONS, SUM(AMOUNT) AS TOTAL_AMOUNT,
               COUNT_IF(LABEL<>'NORMAL') AS FLAGGED
        FROM REGINTEL360.RISK.TRANSACTIONS GROUP BY COUNTRY ORDER BY TOTAL_AMOUNT DESC
    """)


@st.cache_data(ttl=300)
def load_top_risk_customers():
    return conn.query("""
        SELECT t.CUSTOMER_ID,
               COUNT(DISTINCT t.TRANSACTION_ID) AS TOTAL_TXNS,
               COUNT_IF(t.LABEL<>'NORMAL')       AS FLAGGED_TXNS,
               COALESCE(MAX(a.RISK_SCORE),0)     AS MAX_RISK_SCORE,
               ROUND(SUM(t.AMOUNT),2)            AS TOTAL_AMOUNT
        FROM REGINTEL360.RISK.TRANSACTIONS t
        LEFT JOIN REGINTEL360.RISK.RISK_ALERTS a ON t.TRANSACTION_ID=a.TRANSACTION_ID
        GROUP BY t.CUSTOMER_ID HAVING FLAGGED_TXNS>0
        ORDER BY MAX_RISK_SCORE DESC, FLAGGED_TXNS DESC LIMIT 20
    """)


@st.cache_data(ttl=300)
def load_alerts(pattern_tuple, min_score):
    df = conn.query("""
        SELECT ALERT_ID, TRANSACTION_ID, CUSTOMER_ID, PATTERN,
               RISK_SCORE, REASON, CREATED_AT
        FROM REGINTEL360.RISK.RISK_ALERTS ORDER BY RISK_SCORE DESC
    """)
    if pattern_tuple:
        df = df[df["PATTERN"].isin(pattern_tuple)]
    df = df[df["RISK_SCORE"] >= min_score]
    return df


@st.cache_data(ttl=60)
def load_feed_history():
    return conn.query("""
        SELECT FEED_SOURCE, TABLE_NAME, FILE_NAME, ROWS_LOADED, STATUS,
               ERROR_MESSAGE, LOADED_AT, LOADED_BY
        FROM REGINTEL360.RISK.FEED_HISTORY
        ORDER BY LOADED_AT DESC LIMIT 50
    """)


@st.cache_data(ttl=60)
def load_stage_files():
    return conn.query("LIST @REGINTEL360.RISK.FEED_STAGE")


@st.cache_data(ttl=60)
def load_task_status():
    return conn.query("""
        SELECT NAME, STATE, SCHEDULE, LAST_COMMITTED_ON, LAST_SUSPENDED_ON, COMMENT
        FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
            SCHEDULED_TIME_RANGE_START => DATEADD('hour', -24, CURRENT_TIMESTAMP()),
            TASK_NAME => 'AUTO_INGEST_TRANSACTIONS'))
        UNION ALL
        SELECT NAME, STATE, SCHEDULE, LAST_COMMITTED_ON, LAST_SUSPENDED_ON, COMMENT
        FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
            SCHEDULED_TIME_RANGE_START => DATEADD('hour', -24, CURRENT_TIMESTAMP()),
            TASK_NAME => 'AUTO_INGEST_DOCUMENTS'))
        ORDER BY LAST_COMMITTED_ON DESC NULLS LAST
        LIMIT 20
    """)


@st.cache_data(ttl=60)
def load_task_state():
    conn.query("SHOW TASKS IN SCHEMA REGINTEL360.RISK")
    return conn.query("""
        SELECT "name" AS NAME, "state" AS STATE, "schedule" AS SCHEDULE
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
        WHERE "name" IN ('AUTO_INGEST_TRANSACTIONS', 'AUTO_INGEST_DOCUMENTS')
    """)


# ═══════════════════════ HELPERS ═══════════════════════
def extract_and_run_sql(text):
    match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    sql = match.group(1).strip()
    # Auto-fix: prefix bare table names with REGINTEL360.RISK.
    for tbl in ["TRANSACTIONS", "RISK_ALERTS", "REGULATORY_DOCUMENTS", "FEED_HISTORY"]:
        sql = re.sub(
            rf'(?<!\.)(?<!\w){tbl}(?!\w)',
            f'REGINTEL360.RISK.{tbl}',
            sql
        )
    # Remove any accidental double-prefix
    sql = sql.replace("REGINTEL360.RISK.REGINTEL360.RISK.", "REGINTEL360.RISK.")
    try:
        return conn.query(sql)
    except Exception as e:
        return f"Query error: {e}"


def build_messages(history, user_prompt):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-6:]:
        msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": user_prompt})
    return msgs


def clear_all_caches():
    for fn in [load_kpis, load_label_breakdown, load_pattern_distribution,
               load_country_breakdown, load_top_risk_customers, load_alerts,
               load_feed_history, load_stage_files, load_task_state]:
        fn.clear()


def generate_html_report():
    kpis = load_kpis().iloc[0]
    labels = load_label_breakdown()
    patterns = load_pattern_distribution()
    countries = load_country_breakdown()
    customers = load_top_risk_customers().head(10)
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    t = lambda df: df.to_html(index=False, border=0, classes="data-table")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>RegIntel 360 Risk Report</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;margin:40px;color:#1a1a2e}}
  h1{{color:#16213e;border-bottom:3px solid #0f3460;padding-bottom:10px}}
  h2{{color:#0f3460;margin-top:30px;border-bottom:1px solid #e0e0e0;padding-bottom:5px}}
  .kpi-row{{display:flex;gap:20px;margin:20px 0;flex-wrap:wrap}}
  .kpi-card{{background:#f0f2f6;border-radius:8px;padding:15px 25px;text-align:center;min-width:140px;border-left:4px solid #0f3460}}
  .kpi-card .value{{font-size:28px;font-weight:bold;color:#0f3460}}
  .kpi-card .label{{font-size:12px;color:#555;text-transform:uppercase}}
  .data-table{{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}}
  .data-table th{{background:#0f3460;color:white;padding:8px 12px;text-align:left}}
  .data-table td{{padding:6px 12px;border-bottom:1px solid #e0e0e0}}
  .data-table tr:nth-child(even){{background:#f8f9fa}}
  .footer{{margin-top:40px;padding-top:15px;border-top:2px solid #e0e0e0;font-size:11px;color:#888}}
  .alert{{background:#fff3cd;border-left:4px solid #ffc107;padding:10px 15px;margin:15px 0;border-radius:4px;font-size:13px}}
  @media print{{body{{margin:20px}}.kpi-card{{break-inside:avoid}}}}
</style></head><body>
<h1>RegIntel 360 — Risk Intelligence Report</h1>
<p><strong>Generated:</strong> {now}</p>
<div class="alert">Synthetic demo data. Not legal or regulatory advice.</div>
<h2>Key Risk Indicators</h2>
<div class="kpi-row">
  <div class="kpi-card"><div class="value">{int(kpis['TXN_COUNT']):,}</div><div class="label">Transactions</div></div>
  <div class="kpi-card"><div class="value">{int(kpis['ALERT_COUNT']):,}</div><div class="label">Risk Alerts</div></div>
  <div class="kpi-card"><div class="value">{int(kpis['DOC_COUNT']):,}</div><div class="label">Policy Docs</div></div>
  <div class="kpi-card"><div class="value">{int(kpis['HIGH_RISK']):,}</div><div class="label">High Risk</div></div>
  <div class="kpi-card"><div class="value">{kpis['FRAUD_RATE']}%</div><div class="label">Fraud Rate</div></div>
</div>
<h2>Transaction Breakdown by Label</h2>{t(labels)}
<h2>Fraud Pattern Distribution</h2>{t(patterns)}
<h2>Transaction Exposure by Country</h2>{t(countries)}
<h2>Top 10 Highest-Risk Customers</h2>{t(customers)}
<div class="footer"><p>RegIntel 360 &bull; {now} &bull; Synthetic data only.</p>
<p>Print &rarr; Save as PDF</p></div></body></html>"""


# ═══════════════════════ SIDEBAR ═══════════════════════
with st.sidebar:
    st.header("Filters")
    pattern_options = ["STRUCTURING", "RAPID_VELOCITY", "HIGH_RISK_MERCHANT"]
    pattern_filter = st.multiselect("Alert Pattern", pattern_options)
    min_score = st.slider("Min Risk Score", 0, 100, 0)
    st.divider()
    if st.button("Refresh Data", use_container_width=True, on_click=clear_all_caches):
        st.rerun()


# ═══════════════════════ HEADER & TABS ═══════════════════════
st.title("🛡️ RegIntel 360")
st.caption("Risk, Fraud & Regulatory Intelligence — synthetic demo environment")

tab_dashboard, tab_copilot, tab_upload, tab_s3feed, tab_report = st.tabs(
    ["Dashboard", "Risk Copilot", "Upload Data", "S3 Feed", "Download Report"])


# ═══════════════════════ DASHBOARD ═══════════════════════
with tab_dashboard:
    with st.spinner("Loading metrics..."):
        kpis = load_kpis().iloc[0]

    with st.container(horizontal=True):
        st.metric("Transactions", f"{int(kpis['TXN_COUNT']):,}", border=True)
        st.metric("Risk Alerts",  f"{int(kpis['ALERT_COUNT']):,}", border=True)
        st.metric("Policy Docs",  f"{int(kpis['DOC_COUNT']):,}", border=True)
        st.metric("High Risk (>=60)", f"{int(kpis['HIGH_RISK']):,}", border=True)
        st.metric("Fraud Rate",   f"{kpis['FRAUD_RATE']}%", border=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Transactions by Label")
            st.bar_chart(load_label_breakdown(), x="LABEL", y="TRANSACTIONS",
                         color="LABEL", horizontal=True)
    with col2:
        with st.container(border=True):
            st.subheader("Fraud Pattern Distribution")
            st.bar_chart(load_pattern_distribution(), x="PATTERN", y="ALERTS",
                         color="PATTERN", horizontal=True)

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.subheader("Transaction Value by Country")
            st.bar_chart(load_country_breakdown(), x="COUNTRY", y="TOTAL_AMOUNT")
    with col4:
        with st.container(border=True):
            st.subheader("Top Risk Customers")
            st.dataframe(
                load_top_risk_customers(), use_container_width=True, hide_index=True,
                column_config={
                    "MAX_RISK_SCORE": st.column_config.ProgressColumn(
                        "Max Risk Score", min_value=0, max_value=100, format="%d"),
                    "TOTAL_AMOUNT": st.column_config.NumberColumn(
                        "Total Amount", format="$%.2f"),
                })

    with st.container(border=True):
        st.subheader("Risk Alerts")
        st.dataframe(load_alerts(tuple(pattern_filter), min_score),
                     use_container_width=True, hide_index=True)


# ═══════════════════════ RISK COPILOT ═══════════════════════
with tab_copilot:
    st.subheader("Risk Copilot")
    st.caption("Powered by Snowflake Cortex AI — generates SQL, runs it, returns formatted results.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    SUGGESTIONS = {
        "Highest risk customers":
            "Which customers have the highest risk scores? Show top 10 with alert counts.",
        "Structuring by country":
            "Show all STRUCTURING transactions grouped by country with total amounts.",
        "Common fraud patterns":
            "What are the most common fraud patterns and their average risk scores?",
        "High-value flagged txns":
            "Show the top 5 highest-amount transactions not labeled NORMAL, with all columns.",
        "Recent feed history":
            "Show the last 10 rows from REGINTEL360.RISK.FEED_HISTORY ordered by LOADED_AT desc.",
    }

    if not st.session_state.messages:
        selected = st.pills("Try asking:", list(SUGGESTIONS.keys()),
                            label_visibility="collapsed")
        if selected:
            st.session_state.messages.append(
                {"role": "user", "content": SUGGESTIONS[selected]})
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "dataframe" in msg:
                st.dataframe(msg["dataframe"], use_container_width=True, hide_index=True)

    if prompt := st.chat_input("Ask a risk or compliance question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Cortex AI is analyzing..."):
                messages = build_messages(st.session_state.messages[:-1], prompt)
                try:
                    response = cortex_complete(messages)
                except Exception as e:
                    response = f"Error calling Cortex AI: {e}"
            st.markdown(response)
            result_df = extract_and_run_sql(response)
            msg_entry = {"role": "assistant", "content": response}
            if isinstance(result_df, str):
                st.error(result_df)
            elif result_df is not None and not result_df.empty:
                st.dataframe(result_df, use_container_width=True, hide_index=True)
                msg_entry["dataframe"] = result_df
            st.session_state.messages.append(msg_entry)

    if st.session_state.messages:
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.rerun()


# ═══════════════════════ MANUAL UPLOAD ═══════════════════════
with tab_upload:
    st.subheader("Manual Upload")
    st.caption("Upload CSV files directly to append records to the tables.")

    upload_type = st.radio("What are you uploading?",
                           ["Transactions", "Regulatory Documents"], horizontal=True)

    if upload_type == "Transactions":
        st.markdown("**Expected columns:** `TRANSACTION_ID, CUSTOMER_ID, TRANSACTION_TS, "
                    "COUNTRY, CURRENCY, AMOUNT, CHANNEL, MERCHANT_CATEGORY, PAYMENT_METHOD, LABEL`")
        with st.expander("Download sample CSV"):
            try:
                with open("sample_transactions.csv", "r") as f:
                    st.download_button("sample_transactions.csv", f.read(),
                                       "sample_transactions.csv", "text/csv")
            except FileNotFoundError:
                st.info("Sample file not bundled.")

        uploaded = st.file_uploader("Upload transactions CSV", type=["csv"], key="txn_upload")
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                expected = {"TRANSACTION_ID", "CUSTOMER_ID", "TRANSACTION_TS", "COUNTRY",
                            "CURRENCY", "AMOUNT", "CHANNEL", "MERCHANT_CATEGORY",
                            "PAYMENT_METHOD", "LABEL"}
                missing = expected - set(df.columns)
                if missing:
                    st.error(f"Missing columns: {', '.join(sorted(missing))}")
                else:
                    st.success(f"Parsed {len(df)} rows.")
                    st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                    if st.button("Insert into TRANSACTIONS", type="primary", key="ins_txn"):
                        with st.spinner("Inserting..."):
                            session = conn.session()
                            session.create_dataframe(df).write.mode("append").save_as_table(
                                "REGINTEL360.RISK.TRANSACTIONS")
                            session.sql("""INSERT INTO REGINTEL360.RISK.FEED_HISTORY
                                (FEED_SOURCE,TABLE_NAME,FILE_NAME,ROWS_LOADED,STATUS)
                                VALUES ('MANUAL_UPLOAD','TRANSACTIONS',?,?,'SUCCESS')""",
                                params=[uploaded.name, len(df)]).collect()
                            clear_all_caches()
                        st.success(f"Inserted {len(df)} rows.")
                        st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.markdown("**Expected columns:** `DOCUMENT_ID, TITLE, DOMAIN, AUTHORITY, "
                    "EFFECTIVE_DATE, CONTENT`")
        with st.expander("Download sample CSV"):
            try:
                with open("sample_documents.csv", "r") as f:
                    st.download_button("sample_documents.csv", f.read(),
                                       "sample_documents.csv", "text/csv")
            except FileNotFoundError:
                st.info("Sample file not bundled.")

        uploaded = st.file_uploader("Upload documents CSV", type=["csv"], key="doc_upload")
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                expected = {"DOCUMENT_ID", "TITLE", "DOMAIN", "AUTHORITY",
                            "EFFECTIVE_DATE", "CONTENT"}
                missing = expected - set(df.columns)
                if missing:
                    st.error(f"Missing columns: {', '.join(sorted(missing))}")
                else:
                    st.success(f"Parsed {len(df)} documents.")
                    st.dataframe(df[["DOCUMENT_ID","TITLE","DOMAIN","AUTHORITY","EFFECTIVE_DATE"]].head(10),
                                 use_container_width=True, hide_index=True)
                    if st.button("Insert into REGULATORY_DOCUMENTS", type="primary", key="ins_doc"):
                        with st.spinner("Inserting..."):
                            session = conn.session()
                            session.create_dataframe(df).write.mode("append").save_as_table(
                                "REGINTEL360.RISK.REGULATORY_DOCUMENTS")
                            session.sql("""INSERT INTO REGINTEL360.RISK.FEED_HISTORY
                                (FEED_SOURCE,TABLE_NAME,FILE_NAME,ROWS_LOADED,STATUS)
                                VALUES ('MANUAL_UPLOAD','REGULATORY_DOCUMENTS',?,?,'SUCCESS')""",
                                params=[uploaded.name, len(df)]).collect()
                            clear_all_caches()
                        st.success(f"Inserted {len(df)} documents.")
                        st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")


# ═══════════════════════ S3 / STAGE FEED ═══════════════════════
with tab_s3feed:
    st.subheader("S3 / Stage Feed Management")
    st.caption("Manage the automated data feed pipeline. Files land on the stage "
               "(via S3 external stage or direct PUT) and are auto-ingested every 5 minutes.")

    # ── Architecture diagram ──
    with st.expander("Pipeline Architecture", expanded=False):
        st.markdown("""
        ```
        ┌──────────────┐    sync/PUT     ┌─────────────────────────┐
        │  AWS S3      │ ──────────────► │  @REGINTEL360.RISK      │
        │  Bucket      │                 │  .FEED_STAGE            │
        └──────────────┘                 └────────────┬────────────┘
                                                      │
                                         ┌────────────▼────────────┐
                                         │  Scheduled Tasks        │
                                         │  (every 5 min)          │
                                         │  ┌─ AUTO_INGEST_TXN     │
                                         │  └─ AUTO_INGEST_DOC     │
                                         └────────────┬────────────┘
                                                      │  COPY INTO
                                         ┌────────────▼────────────┐
                                         │  TRANSACTIONS           │
                                         │  REGULATORY_DOCUMENTS   │
                                         │  FEED_HISTORY (log)     │
                                         └─────────────────────────┘
        ```
        **To connect S3:** Create a storage integration and external stage, then
        the same tasks will auto-ingest from S3 instead of the internal stage.
        See the S3 Setup section below.
        """)

    # ── Task controls ──
    st.markdown("### Auto-Ingest Tasks")
    try:
        task_df = load_task_state()
        if task_df.empty:
            st.info("No auto-ingest tasks found. They may not be started yet.")
        else:
            for _, row in task_df.iterrows():
                task_name = row["NAME"]
                state = row["STATE"]
                icon = "🟢" if state == "started" else "🔴"
                col_t1, col_t2, col_t3 = st.columns([3, 1, 1])
                col_t1.markdown(f"{icon} **{task_name}** — `{state}` — Schedule: `{row['SCHEDULE']}`")
                if state != "started":
                    if col_t2.button("Resume", key=f"resume_{task_name}"):
                        conn.session().sql(
                            f"ALTER TASK REGINTEL360.RISK.{task_name} RESUME").collect()
                        load_task_state.clear()
                        st.rerun()
                else:
                    if col_t2.button("Suspend", key=f"suspend_{task_name}"):
                        conn.session().sql(
                            f"ALTER TASK REGINTEL360.RISK.{task_name} SUSPEND").collect()
                        load_task_state.clear()
                        st.rerun()
    except Exception as e:
        st.warning(f"Could not load task status: {e}")

    st.divider()

    # ── Stage file browser ──
    st.markdown("### Files on Feed Stage")
    col_s1, col_s2 = st.columns([3, 1])
    with col_s2:
        if st.button("Refresh Stage", key="refresh_stage"):
            load_stage_files.clear()
            st.rerun()
    try:
        stage_df = load_stage_files()
        if stage_df.empty:
            st.info("No files on the feed stage. Upload below or push from S3.")
        else:
            st.dataframe(stage_df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.info("Stage is empty or inaccessible.")

    # ── Manual stage upload ──
    st.markdown("### Upload to Feed Stage")
    st.caption("Upload a CSV directly to the stage. The next auto-ingest task run "
               "will pick it up automatically, or you can trigger it manually below.")

    feed_target = st.radio("Target table", ["Transactions", "Documents"],
                           horizontal=True, key="feed_target")
    subfolder = "transactions" if feed_target == "Transactions" else "documents"

    stage_file = st.file_uploader(f"Upload CSV to stage/{subfolder}/",
                                  type=["csv"], key="stage_upload")
    if stage_file is not None:
        if st.button("Upload to Stage", type="primary", key="put_stage"):
            with st.spinner("Uploading to stage..."):
                session = conn.session()
                session.file.put_stream(
                    stage_file,
                    f"@REGINTEL360.RISK.FEED_STAGE/{subfolder}/{stage_file.name}",
                    auto_compress=False, overwrite=True)
                load_stage_files.clear()
            st.success(f"Uploaded `{stage_file.name}` to `@FEED_STAGE/{subfolder}/`")

    st.divider()

    # ── Manual trigger ──
    st.markdown("### Trigger Ingestion Now")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("Ingest Transactions Now", use_container_width=True, key="ingest_txn"):
            with st.spinner("Running PROCESS_FEED_FILES for transactions..."):
                try:
                    result = conn.query(
                        "CALL REGINTEL360.RISK.PROCESS_FEED_FILES('TRANSACTIONS', "
                        "'.*transactions.*[.]csv')")
                    clear_all_caches()
                    st.success(result.iloc[0, 0])
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")
    with col_m2:
        if st.button("Ingest Documents Now", use_container_width=True, key="ingest_doc"):
            with st.spinner("Running PROCESS_FEED_FILES for documents..."):
                try:
                    result = conn.query(
                        "CALL REGINTEL360.RISK.PROCESS_FEED_FILES('REGULATORY_DOCUMENTS', "
                        "'.*documents.*[.]csv')")
                    clear_all_caches()
                    st.success(result.iloc[0, 0])
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")

    st.divider()

    # ── Feed history ──
    st.markdown("### Feed History")
    try:
        hist_df = load_feed_history()
        if hist_df.empty:
            st.info("No ingestion history yet.")
        else:
            st.dataframe(hist_df, use_container_width=True, hide_index=True,
                         column_config={
                             "ROWS_LOADED": st.column_config.NumberColumn(format="%d"),
                             "STATUS": st.column_config.TextColumn(),
                         })
    except Exception:
        st.info("Feed history table not found.")

    st.divider()

    # ── S3 external stage setup guide ──
    with st.expander("S3 External Stage Setup (for production)", expanded=False):
        st.markdown(f"""
### Step 1: Create Storage Integration
```sql
CREATE OR REPLACE STORAGE INTEGRATION REGINTEL360_S3_INT
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::<YOUR_AWS_ACCOUNT_ID>:role/regintel360-snowflake-role'
  STORAGE_ALLOWED_LOCATIONS = ('s3://regintel360-feed/documents/');
```

### Step 2: Get Snowflake IAM User (for AWS trust policy)
```sql
DESC INTEGRATION REGINTEL360_S3_INT;
-- Note: STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID
```

### Step 3: Create AWS IAM Role
In AWS IAM, create a role with this trust policy:
```json
{{
  "Version": "2012-10-17",
  "Statement": [{{
    "Effect": "Allow",
    "Principal": {{"AWS": "<STORAGE_AWS_IAM_USER_ARN from step 2>"}},
    "Action": "sts:AssumeRole",
    "Condition": {{"StringEquals": {{
      "sts:ExternalId": "<STORAGE_AWS_EXTERNAL_ID from step 2>"
    }}}}
  }}]
}}
```
Attach S3 read policy for `s3://regintel360-feed/documents/*`.

### Step 4: Create External Stage
```sql
CREATE OR REPLACE STAGE REGINTEL360.RISK.S3_FEED_STAGE
  STORAGE_INTEGRATION = REGINTEL360_S3_INT
  URL = 's3://regintel360-feed/documents/'
  FILE_FORMAT = REGINTEL360.RISK.FEED_CSV_FF;
```

### Step 5: Update Tasks to use External Stage
```sql
ALTER TASK REGINTEL360.RISK.AUTO_INGEST_TRANSACTIONS SUSPEND;
ALTER TASK REGINTEL360.RISK.AUTO_INGEST_DOCUMENTS SUSPEND;

-- Recreate with S3 stage
CREATE OR REPLACE TASK REGINTEL360.RISK.AUTO_INGEST_TRANSACTIONS
  WAREHOUSE = COMPUTE_WH SCHEDULE = '5 MINUTE'
AS COPY INTO REGINTEL360.RISK.TRANSACTIONS
   FROM @REGINTEL360.RISK.S3_FEED_STAGE
   PATTERN = '.*transactions.*[.]csv'
   FILE_FORMAT = (FORMAT_NAME = REGINTEL360.RISK.FEED_CSV_FF)
   ON_ERROR = 'CONTINUE';

ALTER TASK REGINTEL360.RISK.AUTO_INGEST_TRANSACTIONS RESUME;
```

### Optional: Snowpipe (event-driven, no polling)
```sql
CREATE OR REPLACE PIPE REGINTEL360.RISK.TXN_PIPE AUTO_INGEST = TRUE AS
  COPY INTO REGINTEL360.RISK.TRANSACTIONS
  FROM @REGINTEL360.RISK.S3_FEED_STAGE
  PATTERN = '.*transactions.*[.]csv'
  FILE_FORMAT = (FORMAT_NAME = REGINTEL360.RISK.FEED_CSV_FF);

-- Get SQS ARN for S3 event notification:
SHOW PIPES LIKE 'TXN_PIPE' IN REGINTEL360.RISK;
-- Configure S3 bucket event → SQS ARN from notification_channel
```
        """)


# ═══════════════════════ DOWNLOAD REPORT ═══════════════════════
with tab_report:
    st.subheader("Download Report")
    col_rpt1, col_rpt2 = st.columns(2)
    with col_rpt1:
        with st.container(border=True):
            st.markdown("**Full Risk Report (HTML)**")
            if st.button("Generate Report", type="primary"):
                with st.spinner("Building report..."):
                    html = generate_html_report()
                st.download_button("Download Risk Report", html,
                    f"regintel360_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                    "text/html", use_container_width=True)
    with col_rpt2:
        with st.container(border=True):
            st.markdown("**Export Raw Data (CSV)**")
            export_table = st.selectbox("Select table",
                ["TRANSACTIONS", "RISK_ALERTS", "REGULATORY_DOCUMENTS", "FEED_HISTORY"])
            if st.button("Export CSV", key="export_csv"):
                with st.spinner(f"Exporting {export_table}..."):
                    df = conn.query(f"SELECT * FROM REGINTEL360.RISK.{export_table}")
                st.download_button(f"Download {export_table}.csv", df.to_csv(index=False),
                    f"{export_table.lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv", use_container_width=True)

    st.divider()
    with st.container(border=True):
        st.markdown("**Report Preview**")
        if st.button("Preview Report"):
            with st.spinner("Building preview..."):
                html = generate_html_report()
            st.components.v1.html(html, height=800, scrolling=True)


# ═══════════════════════ FOOTER ═══════════════════════
st.divider()
st.caption("Demo data and policy corpus are synthetic. Not legal or regulatory advice.")

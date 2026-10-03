# RegIntel 360 — Hackathon Submission

## Project Name
**RegIntel 360** — Risk, Fraud & Regulatory Intelligence Platform

## Team
**Submitter:** GAJENDRAS  
**Account:** HBCSMMR-QU65770

---

## 1. GitHub Repository

**Repository:** *(push pending — run `! gh auth login` in CoCo to complete)*

**Contents:** 28 files across the following structure:
```
RegIntel360/
├── sql/                    # 6 setup SQL scripts
├── data/                   # 5K transactions + 80 regulatory documents
├── cortex_project/         # 2 semantic view YAMLs
├── streamlit-app/          # Deployed Streamlit app (5 tabs + Cortex AI)
├── app/                    # Kernel-mode data viewer
├── eval/                   # 20 evaluation questions
├── docs/                   # Full project documentation + demo script
├── scripts/                # Data generation script
└── prompts/                # CoCo interaction prompts
```

---

## 2. Snowflake Access (for Evaluators)

### Account URL
```
https://HBCSMMR-QU65770.snowflakecomputing.com
```

### Evaluator Credentials

| Email | Snowflake Username | Password | Role |
|-------|-------------------|----------|------|
| evaluator@hack2skill.com | EVALUATOR_HACK2SKILL | RegIntel360_Eval_2026! | REGINTEL360_EVALUATOR |
| hack2skillevaluator@gmail.com | EVALUATOR_HACK2SKILL_GMAIL | RegIntel360_Eval_2026! | REGINTEL360_EVALUATOR |

**Note:** Both accounts require a password change on first login (MUST_CHANGE_PASSWORD = TRUE).

### What Evaluators Can Access
- **Role:** REGINTEL360_EVALUATOR (read-only)
- **Database:** REGINTEL360
- **Schema:** REGINTEL360.RISK
- **Tables:** TRANSACTIONS, RISK_ALERTS, REGULATORY_DOCUMENTS, FEED_HISTORY (SELECT)
- **Semantic Views:** FRAUD_RISK_ANALYTICS, REGINTEL_RISK_SEMANTIC (SELECT)
- **Stages:** DATA_STAGE, FEED_STAGE (READ)
- **Tasks:** AUTO_INGEST_TRANSACTIONS, AUTO_INGEST_DOCUMENTS (MONITOR)
- **Warehouses:** COMPUTE_WH, REGINTEL360_WH (USAGE)

---

## 3. Prototype / MVP — Functional Overview

### Problem
Fraud monitoring, AML investigation, and regulatory evidence are split across transactional systems, case tools, and document repositories. The difficult step is not detection — it's explaining the signal, finding policy evidence, and producing a defensible finding.

### Solution
RegIntel 360 unifies signal detection, evidence gathering, and compliance documentation into one governed Snowflake workflow:

**Signal → Evidence → Policy → Finding → Audit Trail**

### Core Components

| Component | Technology | What It Does |
|-----------|-----------|--------------|
| **Data Foundation** | Snowflake Tables | 5,000+ transactions, 239+ risk alerts, 80+ policy documents |
| **Fraud Detection** | SQL Rules Engine | Structuring, rapid velocity, high-risk merchant, high-value patterns → 0-100 risk scores |
| **Semantic Layer** | Semantic Views (2) | Business-friendly dimensions, metrics, VQRs with descriptions and synonyms |
| **AI Copilot** | Cortex AI (llama3.3-70b) | Natural-language Q&A → auto-generated SQL → formatted results |
| **Data Ingestion** | Scheduled Tasks + S3 Stage | Auto-ingest every 5 min from stage (S3-ready); manual CSV upload |
| **Audit Trail** | FEED_HISTORY table | Every ingestion logged with source, rows, status, user, timestamp |
| **Reporting** | HTML Report Generator | Downloadable risk report with KPIs, charts, tables (PDF via Print) |
| **Application** | Streamlit in Snowflake | 5-tab dashboard: Dashboard, Risk Copilot, Upload, S3 Feed, Download Report |

### Fraud Patterns Detected
| Pattern | Count | Avg Amount | Detection Rule |
|---------|-------|-----------|----------------|
| STRUCTURING | 75 | $9,380 | ≥3 sub-$10K transactions per customer/day |
| RAPID_VELOCITY | 120 | $5,125 | ≥6 transactions per customer/day |
| HIGH_RISK_MERCHANT | 60 | $30,018 | CRYPTO/GAMING/CASH_EQUIVALENT merchants |

### Semantic View Quality
- **FRAUD_RISK_ANALYTICS:** Quality score 76% (Good) — 6 metrics, 5 VQRs, 20 descriptions, 7 is_enum dimensions with sample values
- **REGINTEL_RISK_SEMANTIC:** DDL-created, enhanced with descriptions, synonyms, sample values for natural-language mapping

---

## 4. Streamlit Application

### Deployed Location
**Snowflake Workspace → Untitled → streamlit_app.py**  
(Container Runtime: SYSTEM_COMPUTE_POOL_CPU, Warehouse: COMPUTE_WH)

### 5 Tabs

1. **Dashboard** — KPIs, label/pattern/country charts, top risk customers, filterable alerts
2. **Risk Copilot** — Cortex AI chatbot with suggestion chips, auto-SQL execution, formatted results
3. **Upload Data** — Manual CSV upload for transactions and regulatory documents with validation
4. **S3 Feed** — Pipeline architecture, task controls (resume/suspend), stage browser, manual trigger, feed history audit
5. **Download Report** — HTML risk report generator, CSV export for any table, in-app preview

---

## 5. Demo Script (5 Minutes)

| Time | Action | Talking Point |
|------|--------|---------------|
| 0:00–1:00 | Dashboard tab | Show KPIs: 5K txns, 239 alerts, 5.1% fraud rate, 4 fraud patterns |
| 1:00–2:30 | Risk Copilot tab | Click "Highest risk customers" → AI generates SQL → formatted results. Follow up: "Timeline for CUST00918" |
| 2:30–3:30 | S3 Feed tab | Show architecture, task status (green), trigger ingestion, show feed history audit trail |
| 3:30–4:15 | Upload Data tab | Download sample CSV → re-upload → validate → insert → see updated counts |
| 4:15–5:00 | Download Report tab | Generate HTML report → download → show PDF-ready format. Close: "RegIntel 360 turns fragmented risk evidence into governed, audit-ready intelligence — all inside Snowflake." |

---

## 6. Technical Validation Summary

| Check | Status |
|-------|--------|
| Tables populated | TRANSACTIONS (5,010), RISK_ALERTS (239), REGULATORY_DOCUMENTS (83), FEED_HISTORY (6) |
| Semantic views deployed | FRAUD_RISK_ANALYTICS + REGINTEL_RISK_SEMANTIC — both DESCRIBE OK |
| Auto-ingest tasks | Both STARTED (5-min schedule) |
| Cortex AI | llama3.3-70b — confirmed working |
| Stored procedure | PROCESS_FEED_FILES — validated |
| Stages | DATA_STAGE + FEED_STAGE (directory-enabled) — files present |
| Python syntax | Both .py files compile clean |
| Evaluator access | 2 users created with REGINTEL360_EVALUATOR role |

---

## 7. Why Snowflake

The entire solution runs natively on Snowflake:
- **No external infrastructure** — tables, semantic views, AI, tasks, and the application all live in Snowflake
- **Governed by design** — RBAC, semantic layer, audit trail
- **Production-ready architecture** — S3 integration, Snowpipe, scheduled tasks
- **Cortex AI** — LLM-powered copilot without external API dependencies

---

*Built with Snowflake CoCo (Cortex Code) — October 2026*

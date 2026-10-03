# RegIntel 360 — Complete Project Documentation

## Risk, Fraud & Regulatory Intelligence Platform on Snowflake

---

## 1. Executive Summary

RegIntel 360 is a Snowflake-native fraud detection and regulatory intelligence platform built for banking and NBFC risk/compliance teams. It connects transaction signals with policy/regulatory text so analysts can ask natural-language questions and receive governed, explainable, evidence-backed answers.

**Core workflow:** Signal → Evidence → Policy → Finding → Audit Trail

**Key technologies:** Snowflake Tables, Semantic Views, Cortex AI (LLM), Cortex Search, Scheduled Tasks, Snowpipe-ready S3 integration, Streamlit in Snowflake.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│  ┌────────────┐  ┌────────────────┐  ┌────────────────────────┐    │
│  │ CSV Upload │  │ AWS S3 Bucket  │  │ Internal Feed Stage    │    │
│  │ (Manual)   │  │ (Auto-ingest)  │  │ @FEED_STAGE            │    │
│  └─────┬──────┘  └───────┬────────┘  └───────────┬────────────┘    │
│        │                 │                        │                 │
│        ▼                 ▼                        ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              SNOWFLAKE (REGINTEL360.RISK)                   │    │
│  │                                                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │    │
│  │  │ TRANSACTIONS │  │ RISK_ALERTS  │  │ REGULATORY_DOCS  │  │    │
│  │  │  5,000+ rows │  │  239+ rows   │  │  80+ documents   │  │    │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │    │
│  │         │                 │                    │             │    │
│  │         ▼                 ▼                    ▼             │    │
│  │  ┌─────────────────────────────┐  ┌────────────────────┐   │    │
│  │  │ SEMANTIC VIEWS              │  │ CORTEX SEARCH      │   │    │
│  │  │ • FRAUD_RISK_ANALYTICS      │  │ (Policy Retrieval) │   │    │
│  │  │ • REGINTEL_RISK_SEMANTIC    │  └────────┬───────────┘   │    │
│  │  └──────────────┬──────────────┘           │               │    │
│  │                 │                          │               │    │
│  │                 ▼                          ▼               │    │
│  │         ┌──────────────────────────────────────┐           │    │
│  │         │         CORTEX AI (LLM)              │           │    │
│  │         │    SNOWFLAKE.CORTEX.COMPLETE()        │           │    │
│  │         │    llama3.3-70b                        │           │    │
│  │         └──────────────┬───────────────────────┘           │    │
│  │                        │                                   │    │
│  │  ┌─────────────────────┴────────────────────────────────┐  │    │
│  │  │              AUTO-INGEST PIPELINE                     │  │    │
│  │  │  Tasks (5-min) → PROCESS_FEED_FILES → FEED_HISTORY   │  │    │
│  │  └──────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│        ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              STREAMLIT APPLICATION                           │    │
│  │  ┌───────────┬────────────┬────────────┬──────────┬───────┐ │    │
│  │  │ Dashboard │ Risk       │ Upload     │ S3 Feed  │Download│ │    │
│  │  │ KPIs +    │ Copilot    │ Data       │ Mgmt     │ Report │ │    │
│  │  │ Charts    │ (Cortex AI)│ (Manual)   │ (Auto)   │ (HTML) │ │    │
│  │  └───────────┴────────────┴────────────┴──────────┴───────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Snowflake Objects Inventory

### Database & Schema
| Object | Type |
|--------|------|
| `REGINTEL360` | Database |
| `REGINTEL360.RISK` | Schema |

### Tables
| Table | Rows | Description |
|-------|------|-------------|
| `TRANSACTIONS` | 5,010+ | Individual financial transactions across all channels |
| `RISK_ALERTS` | 239+ | Automated fraud detection alerts with risk scores |
| `REGULATORY_DOCUMENTS` | 83+ | Synthetic policy/regulatory text corpus |
| `FEED_HISTORY` | Dynamic | Audit log of all data ingestions (manual + automated) |

### Semantic Views
| View | Tables | Metrics | VQRs | Description |
|------|--------|---------|------|-------------|
| `FRAUD_RISK_ANALYTICS` | 2 | 6 | 5 | Full-featured view with descriptions, synonyms, sample values, is_enum |
| `REGINTEL_RISK_SEMANTIC` | 2 | 5 | 0 | DDL-created view with enhanced descriptions and synonyms |

### Stages & File Formats
| Object | Type | Purpose |
|--------|------|---------|
| `DATA_STAGE` | Internal Stage | Initial data load |
| `FEED_STAGE` | Internal Stage | S3/manual feed landing zone (directory-enabled) |
| `CSV_FF` | File Format | Initial load format |
| `FEED_CSV_FF` | File Format | Feed ingestion format with error handling |

### Tasks (Auto-Ingest Pipeline)
| Task | Schedule | Target |
|------|----------|--------|
| `AUTO_INGEST_TRANSACTIONS` | Every 5 min | `*transactions*.csv` → TRANSACTIONS |
| `AUTO_INGEST_DOCUMENTS` | Every 5 min | `*documents*.csv` → REGULATORY_DOCUMENTS |

### Stored Procedures
| Procedure | Purpose |
|-----------|---------|
| `PROCESS_FEED_FILES(table, pattern)` | COPY INTO + FEED_HISTORY logging |

### Warehouses
| Warehouse | Size | Purpose |
|-----------|------|---------|
| `REGINTEL360_WH` | X-Small | Dedicated project warehouse |
| `COMPUTE_WH` | Session default | Streamlit + task execution |

---

## 4. Data Model

### TRANSACTIONS
| Column | Type | Description |
|--------|------|-------------|
| TRANSACTION_ID | STRING | Primary key — unique per transaction |
| CUSTOMER_ID | STRING | Customer identifier |
| TRANSACTION_TS | TIMESTAMP_NTZ | When the transaction was processed |
| COUNTRY | STRING | Two-letter country code (10 values) |
| CURRENCY | STRING | ISO currency code: USD, EUR, INR, SGD, GBP |
| AMOUNT | NUMBER(18,2) | Transaction value ($3.58 – $42,790.95) |
| CHANNEL | STRING | ONLINE, MOBILE, API, BRANCH |
| MERCHANT_CATEGORY | STRING | 9 categories including high-risk: CRYPTO, GAMING, CASH_EQUIVALENT |
| PAYMENT_METHOD | STRING | CARD, WIRE, SEPA, ACH, UPI |
| LABEL | STRING | NORMAL (94.9%), STRUCTURING, RAPID_VELOCITY, HIGH_RISK_MERCHANT |

### RISK_ALERTS
| Column | Type | Description |
|--------|------|-------------|
| ALERT_ID | STRING | Primary key — unique per alert |
| TRANSACTION_ID | STRING | FK to TRANSACTIONS |
| CUSTOMER_ID | STRING | Customer who triggered the alert |
| PATTERN | STRING | STRUCTURING, RAPID_VELOCITY, HIGH_RISK_MERCHANT |
| RISK_SCORE | NUMBER(5,2) | 0–100 composite score |
| REASON | STRING | Human-readable rule evidence |
| CREATED_AT | TIMESTAMP_NTZ | When the alert was generated |

### Relationship
```
RISK_ALERTS (many) ──── TRANSACTION_ID ────► TRANSACTIONS (one)
```

### Fraud Detection Rules (from 03_fraud_pattern_generator.sql)
| Signal | Threshold | Score |
|--------|-----------|-------|
| Structuring count (≥3 sub-$10K txns/day) | `struct_cnt >= 3` | +45 pts |
| Rapid velocity (≥6 txns/day) | `daily_cnt >= 6` | +30 pts |
| High-value transaction | `amount >= 25,000` | +15 pts |
| High-risk merchant | CRYPTO, GAMING, CASH_EQUIVALENT | +20 pts |
| **Cap** | | **100** |

---

## 5. Semantic Views — Detail

### FRAUD_RISK_ANALYTICS (YAML-authored, fully enriched)
- **Quality Score:** ~76% (Good)
- **20 descriptions** covering model, tables, and all columns
- **6 metrics:** TOTAL_AMOUNT, TRANSACTION_COUNT, AVERAGE_TRANSACTION_AMOUNT, FLAGGED_TRANSACTION_COUNT, ALERT_COUNT, AVERAGE_RISK_SCORE
- **5 verified queries:** fraud rate, label breakdown, country flagging, merchant risk, pattern analysis
- **7 dimensions** with `is_enum: true` and `sample_values`
- **Synonyms** on all columns for natural-language mapping

### REGINTEL_RISK_SEMANTIC (DDL-authored, enhanced)
- Created via `04_semantic_view.sql` DDL
- Enhanced with descriptions, synonyms, sample_values for:
  - "highest-risk customers" → RISK_SCORE, CUSTOMER_ID, AVERAGE_RISK_SCORE
  - "structuring" → PATTERN, LABEL with synonym "structuring flag"
  - "transaction value by country" → TOTAL_AMOUNT, COUNTRY

---

## 6. Streamlit Application

### Location: `regintel360-app/streamlit_app.py`

### Tab 1: Dashboard
- **KPI row:** Transactions, Risk Alerts, Policy Docs, High Risk (≥60), Fraud Rate
- **Charts:** Label breakdown, fraud pattern distribution, value by country
- **Top Risk Customers table** with progress-bar risk scores
- **Filterable alerts table** (sidebar: pattern multiselect + min score slider)
- All queries cached with `@st.cache_data(ttl=300)` and a Refresh button

### Tab 2: Risk Copilot (Cortex AI)
- Chat interface powered by `SNOWFLAKE.CORTEX.COMPLETE()` via SQL (no Python package dependency)
- Model: `llama3.3-70b`
- Uses string-based prompt with `[SYSTEM]/[USER]/[ASSISTANT]` role markers
- System prompt includes full table schemas
- **5 suggestion chips** for quick demo questions
- Auto-extracts SQL from AI responses, executes it, displays formatted results inline
- Conversation history with clear button

### Tab 3: Upload Data (Manual)
- Toggle between Transactions and Regulatory Documents
- CSV column validation before insert
- Preview with label/domain metrics
- One-click insert via Snowpark `write.mode("append")`
- Logs to FEED_HISTORY table
- Sample CSVs bundled for download

### Tab 4: S3 Feed Management
- **Pipeline architecture diagram** (expandable)
- **Task controls:** Live started/suspended status with Resume/Suspend buttons
- **Stage file browser:** LIST @FEED_STAGE
- **Upload to stage:** Push CSV to stage subfolder for next auto-ingest
- **Manual trigger:** One-click PROCESS_FEED_FILES execution
- **Feed history:** Audit trail of all loads
- **S3 External Stage Setup guide:** Full SQL for storage integration, IAM trust policy, external stage, Snowpipe

### Tab 5: Download Report
- **HTML Risk Report:** Styled, print-ready with KPIs, tables, charts — open in browser → Print → Save as PDF
- **CSV Export:** Download any table (TRANSACTIONS, RISK_ALERTS, REGULATORY_DOCUMENTS, FEED_HISTORY)
- **In-app preview:** Renders the HTML report inline

---

## 7. S3 Integration Pipeline

### Current State (Demo-Ready)
```
Manual Upload / PUT ──► @FEED_STAGE ──► Scheduled Tasks (5 min) ──► Tables
                                               │
                                               ▼
                                         FEED_HISTORY (audit)
```

### Production State (with S3)
```
S3 Bucket (s3://regintel360-feed/documents/)
    │
    ├── transactions/*.csv
    └── documents/*.csv
         │
         ▼
Storage Integration (REGINTEL360_S3_INT)
         │
         ▼
External Stage (@S3_FEED_STAGE)
         │
    ┌────┴────┐
    │ Option A │  Scheduled Tasks (5-min polling)
    │ Option B │  Snowpipe (event-driven via SQS)
    └────┬────┘
         ▼
    TRANSACTIONS / REGULATORY_DOCUMENTS
         │
         ▼
    FEED_HISTORY (audit log)
```

### S3 Setup Steps (detailed in app)
1. Create Storage Integration with AWS IAM role ARN
2. Get Snowflake IAM user ARN for AWS trust policy
3. Create AWS IAM role with trust policy + S3 read access
4. Create external stage pointing to S3
5. Update tasks to use external stage (or create Snowpipe for event-driven)

---

## 8. Project File Structure

```
RegIntel360/
├── README.md
├── manifest.json
├── requirements.txt
├── data/
│   ├── transactions_5000.csv          # Source transaction data
│   └── regulatory_documents_80.csv    # Source policy documents
├── sql/
│   ├── 01_setup_schema.sql            # Database, schema, tables
│   ├── 02_load_data.sql               # File format, stage, COPY INTO
│   ├── 03_fraud_pattern_generator.sql # Risk scoring rules → RISK_ALERTS
│   ├── 04_semantic_view.sql           # REGINTEL_RISK_SEMANTIC DDL
│   ├── 05_cortex_search.sql           # Cortex Search service
│   └── 06_cortex_agent.sql            # Cortex Agent definition
├── app/
│   └── streamlit_app.py               # Kernel-mode data viewer
├── eval/
│   └── evaluation_questions.csv       # 20 test questions
├── prompts/
│   └── coco_prompts.md                # CoCo interaction prompts
├── docs/
│   ├── solution_description.md        # Solution overview
│   └── 3_minute_demo_script.md        # Demo talking points
└── scripts/
    └── generate_dataset.py            # Data generation script

cortex_project/
├── cortex-project.yaml
├── FRAUD_RISK_ANALYTICS.sv.yaml       # Full semantic view (YAML)
└── REGINTEL_RISK_SEMANTIC.sv.yaml     # Enhanced semantic view (YAML)

regintel360-app/                       # Streamlit Application (deployed as REGINTEL360_APP)
├── snowflake.yml                      # App config (COMPUTE_WH + SYSTEM_COMPUTE_POOL_CPU)
├── pyproject.toml                     # Dependencies
├── streamlit_app.py                   # 705-line app (5 tabs + Cortex AI)
├── sample_transactions.csv            # 10 sample rows for upload demo
├── sample_documents.csv               # 3 sample policy documents
└── .streamlit/config.toml             # Theme config
```

---

## 9. Setup Guide (from scratch)

### Prerequisites
- Snowflake account with ACCOUNTADMIN role
- Cortex AI enabled (for Risk Copilot)
- Compute pool available (SYSTEM_COMPUTE_POOL_CPU)

### Step-by-Step

```sql
-- 1. Run setup scripts in order
-- 01_setup_schema.sql  → creates database, schema, tables
-- 02_load_data.sql     → loads CSV data via internal stage
-- 03_fraud_pattern_generator.sql → generates 239 risk alerts

-- 2. Create semantic views
-- 04_semantic_view.sql → REGINTEL_RISK_SEMANTIC
-- Or deploy FRAUD_RISK_ANALYTICS from cortex_project/ YAML

-- 3. Create feed pipeline (already done)
-- File format, feed stage, feed history table
-- Stored procedure PROCESS_FEED_FILES
-- Scheduled tasks AUTO_INGEST_TRANSACTIONS, AUTO_INGEST_DOCUMENTS

-- 4. Resume auto-ingest tasks
ALTER TASK REGINTEL360.RISK.AUTO_INGEST_TRANSACTIONS RESUME;
ALTER TASK REGINTEL360.RISK.AUTO_INGEST_DOCUMENTS RESUME;

-- 5. Deploy Streamlit app
-- Open regintel360-app/ folder in Workspace → click Run
```

---

## 10. Demo Script (5 Minutes)

### Minute 1: Problem & Data Foundation (0:00–1:00)
> "Banks manage fraud signals, transaction risk, and regulatory obligations across separate systems. RegIntel 360 unifies signal detection, evidence gathering, and policy compliance into one governed Snowflake workflow."

1. Open **Dashboard** tab
2. Show KPIs: 5,000 transactions, 239 alerts, 80 policy documents, 5.1% fraud rate
3. Point out the 4 fraud labels and their distribution

### Minute 2: Risk Analysis & AI Copilot (1:00–2:30)
> "Let's investigate. Which customers show the strongest fraud signals?"

1. Switch to **Risk Copilot** tab
2. Click suggestion chip: **"Highest risk customers"**
3. Show the AI generating SQL, executing it, and returning formatted results
4. Ask a follow-up: *"Show the transaction timeline for CUST00918"*
5. Point out the AI identifies the structuring burst pattern automatically

### Minute 3: Data Ingestion & S3 Feed (2:30–3:30)
> "In production, new data flows in automatically from S3."

1. Switch to **S3 Feed** tab
2. Show the pipeline architecture diagram
3. Show task status (green = running every 5 min)
4. Click **"Ingest Transactions Now"** to demo manual trigger
5. Show **Feed History** audit trail
6. Switch back to **Dashboard** → Refresh → show updated counts

### Minute 4: Upload & Document Management (3:30–4:15)
> "Analysts can also upload data directly."

1. Switch to **Upload Data** tab
2. Download `sample_transactions.csv` → re-upload it
3. Show column validation and preview
4. Click Insert → show success with balloons
5. Mention regulatory documents can be uploaded the same way

### Minute 5: Reporting & Close (4:15–5:00)
> "Everything is auditable and exportable."

1. Switch to **Download Report** tab
2. Click **Generate Report** → download the HTML report
3. Click **Preview Report** to show it inline
4. Show CSV export for any table

> **Close:** "RegIntel 360 turns fragmented risk and regulatory evidence into a governed, explainable, audit-ready intelligence workflow — all inside Snowflake. The data is synthetic, but the architecture is production-ready."

---

## 11. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **SQL-based Cortex calls** (`SNOWFLAKE.CORTEX.COMPLETE()`) with string prompt | Works in all Streamlit container runtimes without extra packages; avoids PARSE_JSON VARIANT casting issues |
| **Internal stage + tasks** for feed pipeline | Works immediately without AWS setup; upgradeable to S3 external stage |
| **FEED_HISTORY audit table** | Every ingestion (manual or automated) is logged with source, rows, status, user |
| **Two semantic views** | YAML-authored (FRAUD_RISK_ANALYTICS) for full enrichment; DDL-authored (REGINTEL_RISK_SEMANTIC) showing the SQL approach |
| **Synthetic data, clearly labeled** | Every UI surface and document states data is synthetic |
| **`@st.cache_data(ttl=300)`** on all queries | Fast rerenders; Refresh button clears all caches |
| **HTML report** (not PDF) | No external dependencies; browser Print → PDF works everywhere |

---

## 12. Fraud Pattern Analysis Summary

| Label | Count | % | Avg Amount | Key Signal |
|-------|-------|---|------------|------------|
| NORMAL | 4,745 | 94.9% | $386 | Legitimate activity |
| RAPID_VELOCITY | 120 | 2.4% | $5,125 | ≥6 txns/day per customer |
| STRUCTURING | 75 | 1.5% | $9,380 | Sub-$10K amounts, ≥3/day |
| HIGH_RISK_MERCHANT | 60 | 1.2% | $30,018 | CRYPTO/GAMING/CASH_EQUIVALENT |

**255 flagged transactions (5.1%) account for $3.1M — 63% of total dollar volume.**

### Highest-Risk Customers (Score 65)
Customers combining structuring patterns with high-risk merchants:
CUST00918 (CRYPTO), CUST00922 (GAMING), CUST00920 (CRYPTO+GAMING),
CUST00917 (CASH_EQUIVALENT+GAMING), CUST00916 (CASH_EQUIVALENT+GAMING)

---

## 13. Limitations & Disclaimers

- All transaction data, risk alerts, and regulatory documents are **synthetic**
- Regulatory documents are templated placeholders, not real regulations
- Risk scores use simplified rule-based logic, not ML models
- The S3 integration requires AWS configuration (IAM role, trust policy) for production use
- Cortex AI responses should be validated by compliance professionals
- **This is not legal or regulatory advice**

---

## 14. Future Extensions

- Replace synthetic policies with licensed regulatory content
- Add sanctions/PEP screening data
- Implement ML-based anomaly detection (Snowflake ML)
- Stream transactions with Dynamic Tables for real-time processing
- Add Cortex Search for policy RAG (retrieval-augmented generation)
- Add Cortex Agent for multi-tool orchestration
- Implement row-access policies and role-based masking
- Add case management workflow integration
- Capture agent evaluation metrics and human disposition feedback
- Connect to real S3 feeds with Snowpipe event-driven ingestion

---

## 15. Evaluator Access

### Snowflake Login
- **URL:** `https://hbcsmmr-nx77220.snowflakecomputing.com`
- **Password:** `RegIntel360_Eval_2026!`

| Evaluator | Username | Login Email |
|---|---|---|
| Hack2Skill | `EVALUATOR_HACK2SKILL` | `evaluator@hack2skill.com` |
| Hack2Skill Gmail | `EVALUATOR_HACK2SKILL_GMAIL` | `hack2skillevaluator@gmail.com` |

**Role:** `REGINTEL360_EVALUATOR` (19 grants: database, schema, all tables, semantic views, warehouse, Streamlit app, stages, tasks)

### Streamlit App URL
```
https://app.snowflake.com/hbcsmmr/nx77220/#/streamlit-apps/REGINTEL360.RISK.REGINTEL360_APP
```

---

*Generated by Snowflake CoCo (Cortex Code) — October 2026*

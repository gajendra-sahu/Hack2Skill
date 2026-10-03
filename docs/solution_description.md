# RegIntel 360 — Risk, Fraud & Regulatory Intelligence Copilot

## Executive summary
RegIntel 360 is a Snowflake-native copilot for banking and NBFC risk/compliance teams. It connects transaction signals with policy/regulatory text so a business, fraud or compliance user can ask natural-language questions and receive governed, explainable, evidence-backed answers.

## Problem
Fraud monitoring, AML investigation, liquidity/credit-risk review and regulatory evidence are often split across transactional systems, case tools, data warehouses and document repositories. The difficult step is not only detecting a signal; it is explaining the signal, finding the relevant control/policy evidence and producing a defensible finding.

## Core workflow
**Signal → Evidence → Policy → Finding → Audit trail**

1. Transaction data lands in Snowflake.
2. Explainable fraud rules generate candidate alerts and risk scores.
3. A native Semantic View gives business meaning to transactions and alerts.
4. Cortex Search indexes the policy/regulatory corpus.
5. Cortex Agent orchestrates structured analytics and document retrieval.
6. Streamlit provides a risk cockpit for analysts and executives.
7. Evaluation questions test structured, retrieval, hybrid and grounding behavior.

## Architecture
User → Streamlit Risk Cockpit → Cortex Agent → (RiskAnalytics / Semantic View → Transactions + Risk Alerts) + (RegulatorySearch / Cortex Search → Policy Documents) → evidence-backed response.

## Fraud patterns included
- Structuring: repeated transactions below a threshold within a customer/day cluster.
- Rapid velocity: unusually high transaction frequency in a short/day window.
- High-risk merchant: crypto/gaming/cash-equivalent categories in the synthetic model.
- High value: unusually large individual transactions.
- Composite scoring: signals accumulate into an explainable 0–100 risk score.

## Why Snowflake
The solution keeps structured data, semantic definitions, document retrieval, agent orchestration and the application close to the governed data platform. This minimizes copies and demonstrates a realistic enterprise deployment pattern.

## Judging alignment
**Real-world relevance:** targets the expensive manual handoff between fraud/risk signals and compliance evidence.

**Technical execution:** combines native Snowflake tables, SQL rules, Semantic Views, Cortex Search, Cortex Agents and Streamlit.

**Solution completeness:** includes data generation, ingestion, detection, semantic analytics, retrieval, agent orchestration, UI, evaluation and demo assets.

**Explainability/governance:** outputs can reference transaction/customer IDs, explicit rule evidence and source document IDs; the demo corpus is clearly marked synthetic.

## Demo story
A compliance analyst asks: “Which customers show structuring behavior, and which policy evidence should I review?” RegIntel 360 identifies the relevant customers and transactions through structured analytics, retrieves policy evidence through Cortex Search and returns a concise finding with traceable IDs.

## Future extensions
Replace synthetic policies with licensed/approved regulatory content; add sanctions/PEP data; add graph/network features; stream transactions with Dynamic Tables/Streams; add case-management integration; add role-based masking and row-access policies; capture agent evaluation/feedback and human disposition.

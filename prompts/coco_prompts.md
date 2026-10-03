# RegIntel 360 — CoCo Prompt Pack

## Build / validate
1. Inspect REGINTEL360.RISK.TRANSACTIONS and RISK_ALERTS. Recommend business-friendly dimensions, facts and metrics for a fraud/risk semantic view.
2. Validate REGINTEL_RISK_SEMANTIC and add descriptions/synonyms so questions such as “highest-risk customers”, “structuring”, and “transaction value by country” map correctly.
3. Inspect REGULATORY_SEARCH. Verify CONTENT is the retrieval field and DOMAIN/AUTHORITY can be used as filters.
4. Review REGINTEL360_AGENT. Ensure structured questions use RiskAnalytics, policy questions use RegulatorySearch, and hybrid questions can use both.
5. Strengthen grounding: never invent a regulatory obligation; cite RI360 document IDs; state that the supplied corpus is synthetic.

## Demo prompts
- Which five customers have the strongest fraud-risk evidence? Explain the signals.
- Find customers showing structuring behavior and show the supporting transaction IDs.
- Which synthetic policies describe transaction-monitoring escalation and evidence retention?
- Connect the highest-risk structuring case to the most relevant policy evidence.
- Produce an audit-ready analyst finding with signal, evidence, policy reference and recommended next review step.

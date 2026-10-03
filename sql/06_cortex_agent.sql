USE DATABASE REGINTEL360; USE SCHEMA RISK;
CREATE OR REPLACE AGENT REGINTEL360_AGENT
COMMENT='Risk, Fraud and Regulatory Intelligence Copilot'
FROM SPECIFICATION $$
models:
  orchestration: auto
instructions:
  response: |
    You are RegIntel 360, a banking risk, fraud and regulatory intelligence copilot.
    Use RiskAnalytics for transaction/alert questions and RegulatorySearch for policy evidence.
    For hybrid questions, connect risk signals to relevant policy evidence.
    Always include transaction/customer identifiers when available and document IDs for policy claims.
    State clearly that the bundled policy corpus is synthetic demonstration content, not legal advice.
tools:
  - tool_spec:
      type: cortex_analyst_text_to_sql
      name: RiskAnalytics
      description: Analyze transactions, customers, fraud alerts, patterns, amounts and risk scores.
  - tool_spec:
      type: cortex_search
      name: RegulatorySearch
      description: Retrieve relevant evidence from synthetic regulatory and internal policy documents.
tool_resources:
  RiskAnalytics:
    semantic_view: REGINTEL360.RISK.REGINTEL_RISK_SEMANTIC
  RegulatorySearch:
    search_service: REGINTEL360.RISK.REGULATORY_SEARCH
    max_results: '8'
$$;

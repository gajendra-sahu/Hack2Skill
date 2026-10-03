from snowflake.snowpark.context import get_active_session

session = get_active_session()

# -- KPI Summary --
print("=" * 60)
print("  RegIntel 360 — Risk, Fraud & Regulatory Intelligence")
print("=" * 60)

txn_count = session.sql("SELECT COUNT(*) AS C FROM REGINTEL360.RISK.TRANSACTIONS").collect()[0]["C"]
alert_count = session.sql("SELECT COUNT(*) AS C FROM REGINTEL360.RISK.RISK_ALERTS").collect()[0]["C"]
doc_count = session.sql("SELECT COUNT(*) AS C FROM REGINTEL360.RISK.REGULATORY_DOCUMENTS").collect()[0]["C"]
high_risk = session.sql("SELECT COUNT(*) AS C FROM REGINTEL360.RISK.RISK_ALERTS WHERE RISK_SCORE >= 60").collect()[0]["C"]

print(f"\n  Transactions: {txn_count:,}")
print(f"  Risk Alerts:  {alert_count:,}")
print(f"  Policy Docs:  {doc_count:,}")
print(f"  High Risk:    {high_risk:,}")

# -- Fraud Label Breakdown --
print("\n" + "-" * 60)
print("  Transaction Breakdown by Label")
print("-" * 60)
label_df = session.sql("""
    SELECT LABEL, COUNT(*) AS TRANSACTIONS, ROUND(SUM(AMOUNT), 2) AS TOTAL_AMOUNT
    FROM REGINTEL360.RISK.TRANSACTIONS
    GROUP BY LABEL ORDER BY TRANSACTIONS DESC
""").to_pandas()
print(label_df.to_string(index=False))

# -- Fraud Pattern Distribution --
print("\n" + "-" * 60)
print("  Fraud Pattern Distribution")
print("-" * 60)
pattern_df = session.sql("""
    SELECT PATTERN, COUNT(*) AS ALERTS, ROUND(AVG(RISK_SCORE), 1) AS AVG_SCORE
    FROM REGINTEL360.RISK.RISK_ALERTS
    GROUP BY PATTERN ORDER BY ALERTS DESC
""").to_pandas()
print(pattern_df.to_string(index=False))

# -- Top Risk Customers --
print("\n" + "-" * 60)
print("  Top 10 Risk Customers")
print("-" * 60)
cust_df = session.sql("""
    SELECT t.CUSTOMER_ID,
           COUNT(DISTINCT t.TRANSACTION_ID) AS TOTAL_TXNS,
           COUNT_IF(t.LABEL <> 'NORMAL') AS FLAGGED_TXNS,
           COALESCE(MAX(a.RISK_SCORE), 0) AS MAX_RISK_SCORE,
           ROUND(SUM(t.AMOUNT), 2) AS TOTAL_AMOUNT
    FROM REGINTEL360.RISK.TRANSACTIONS t
    LEFT JOIN REGINTEL360.RISK.RISK_ALERTS a ON t.TRANSACTION_ID = a.TRANSACTION_ID
    GROUP BY t.CUSTOMER_ID
    HAVING FLAGGED_TXNS > 0
    ORDER BY MAX_RISK_SCORE DESC, FLAGGED_TXNS DESC
    LIMIT 10
""").to_pandas()
print(cust_df.to_string(index=False))

# -- Recent Alerts --
print("\n" + "-" * 60)
print("  Top 10 Risk Alerts (by score)")
print("-" * 60)
alerts_df = session.sql("""
    SELECT ALERT_ID, TRANSACTION_ID, CUSTOMER_ID, PATTERN, RISK_SCORE
    FROM REGINTEL360.RISK.RISK_ALERTS
    ORDER BY RISK_SCORE DESC
    LIMIT 10
""").to_pandas()
print(alerts_df.to_string(index=False))

print("\n" + "=" * 60)
print("  Demo data is synthetic. Not legal or regulatory advice.")
print("=" * 60)

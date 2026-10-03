USE DATABASE REGINTEL360; USE SCHEMA RISK;
CREATE OR REPLACE SEMANTIC VIEW REGINTEL_RISK_SEMANTIC
TABLES (
 transactions AS REGINTEL360.RISK.TRANSACTIONS PRIMARY KEY (TRANSACTION_ID),
 alerts AS REGINTEL360.RISK.RISK_ALERTS PRIMARY KEY (ALERT_ID)
)
RELATIONSHIPS (
 tx_alert AS alerts(TRANSACTION_ID) REFERENCES transactions(TRANSACTION_ID)
)
FACTS (
 transactions.amount AS AMOUNT,
 alerts.risk_score AS RISK_SCORE
)
DIMENSIONS (
 transactions.transaction_id AS TRANSACTION_ID,
 transactions.customer_id AS CUSTOMER_ID,
 transactions.transaction_ts AS TRANSACTION_TS,
 transactions.country AS COUNTRY,
 transactions.currency AS CURRENCY,
 transactions.channel AS CHANNEL,
 transactions.merchant_category AS MERCHANT_CATEGORY,
 alerts.alert_id AS ALERT_ID,
 alerts.pattern AS PATTERN
)
METRICS (
 transactions.transaction_count AS COUNT(transactions.TRANSACTION_ID),
 transactions.total_amount AS SUM(transactions.AMOUNT),
 alerts.alert_count AS COUNT(alerts.ALERT_ID),
 alerts.average_risk_score AS AVG(alerts.RISK_SCORE)
)
COMMENT='RegIntel 360 transaction and fraud-risk semantic layer';

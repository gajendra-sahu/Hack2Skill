# RegIntel 360

**Risk, Fraud & Regulatory Intelligence Copilot** for the Snowflake CoCo / Hack2Skill hackathon.

## Included
- Snowflake database/schema/table DDL
- 5,000 synthetic transactions
- 80 synthetic regulatory/policy documents
- SQL fraud-pattern generator and risk scoring
- Native Semantic View
- Cortex Search service
- Cortex Agent specification
- Streamlit risk cockpit
- 20 evaluation questions
- CoCo prompt pack
- 3-minute demo script
- Full solution/business description

## Run order
1. `sql/01_setup_schema.sql`
2. Upload both CSV files from `data/` to the Snowflake stage.
3. `sql/02_load_data.sql`
4. `sql/03_fraud_pattern_generator.sql`
5. `sql/04_semantic_view.sql`
6. `sql/05_cortex_search.sql`
7. `sql/06_cortex_agent.sql`
8. Create Streamlit in Snowflake and use `app/streamlit_app.py`.
9. Validate with `eval/evaluation_questions.csv`.

## Suggested headline demo
> Which customers show structuring behavior, what transaction evidence supports the signal, and which policy documents should an analyst review?

## Safety / data note
All data and policy text in this package are synthetic demonstration content. Do not present the synthetic documents as actual law, regulatory guidance or legal advice.

## Snowflake compatibility note
Snowflake capabilities evolve quickly. The project follows the current native Semantic View + Cortex Search + Cortex Agent architecture. Check account/region availability and required privileges before deployment.

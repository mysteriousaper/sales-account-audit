"""Run the account-work rules on a public CRM export I did not create (no answer key)."""
import json
import duckdb

con = duckdb.connect()
for t in ["sales_pipeline", "accounts", "products", "sales_teams"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('data/external/maven_crm/{t}.csv')")
con.execute(open("sql/05_maven_rules.sql").read())
q = lambda s: con.execute(s).fetchall()
out = {"opportunities": q("SELECT COUNT(*) FROM sales_pipeline")[0][0],
       "agents": q("SELECT COUNT(DISTINCT sales_agent) FROM sales_pipeline")[0][0],
       "stages": dict(q("SELECT deal_stage, COUNT(*) FROM sales_pipeline GROUP BY 1")),
       "flags_by_rule": dict(q("SELECT rule, COUNT(*) FROM m_flags GROUP BY 1 ORDER BY 2 DESC")),
       "opportunities_flagged": q("SELECT COUNT(DISTINCT opportunity_id) FROM m_flags")[0][0],
       "unknown_product_names": q("SELECT product, COUNT(*) FROM sales_pipeline s WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.product=s.product) GROUP BY 1"),
       "sector_values": q("SELECT sector, COUNT(*) FROM accounts GROUP BY 1 ORDER BY 1"),
       "last_date_in_export": str(q("SELECT max(close_date) FROM sales_pipeline")[0][0])}
stale = q("""SELECT t.manager, s.sales_agent, COUNT(*) AS engaging,
                    SUM(CASE WHEN f.opportunity_id IS NOT NULL THEN 1 ELSE 0 END) AS stale
             FROM sales_pipeline s JOIN sales_teams t USING (sales_agent)
             LEFT JOIN m_flags f ON f.opportunity_id = s.opportunity_id AND f.rule = 'M8_stale_engaging'
             WHERE s.deal_stage = 'Engaging' GROUP BY 1, 2 ORDER BY stale DESC LIMIT 5""")
out["top_agents_by_stale_engaging"] = stale
out["sample_flags_for_manual_check"] = q("""SELECT f.rule, s.* FROM m_flags f JOIN sales_pipeline s USING (opportunity_id)
                                            USING SAMPLE 12 ROWS""")
print(json.dumps(out, indent=1, default=str))
json.dump(out, open("results_maven.json", "w"), indent=2, default=str)

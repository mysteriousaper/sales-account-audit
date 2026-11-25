"""
Scale test: build 1,000,000 accounts, about 3 million activities and 2.5 million contacts
inside DuckDB, then run the same six rules from sql/01_rules.sql and time them.
"""
import json
import time
import duckdb

con = duckdb.connect()
con.execute("SET threads TO 4")
t0 = time.time()
con.execute("""
CREATE TABLE accounts AS
SELECT 'A' || i AS account_id,
       'R' || lpad(CAST(1 + (i % 40) AS VARCHAR), 2, '0') AS owner_rep,
       CASE WHEN r < 0.15 THEN 'New' WHEN r < 0.50 THEN 'Working' WHEN r < 0.75 THEN 'Contacted'
            WHEN r < 0.85 THEN 'Demo Scheduled' ELSE 'Disqualified' END AS status,
       CASE WHEN random() < 0.9 THEN DATE '2026-11-20' + CAST(floor(random() * 30) - 5 AS INTEGER) END AS next_step_date,
       CASE WHEN random() < 0.9 THEN 'Not a fit' END AS disqualify_reason
FROM (SELECT range AS i, random() AS r FROM range(1, 1000001))""")
con.execute("""
CREATE TABLE activities AS
SELECT a.account_id,
       CASE WHEN random() < 0.95 THEN a.owner_rep ELSE 'R99' END AS rep,
       CASE WHEN random() < 0.55 THEN 'call' WHEN random() < 0.9 THEN 'email' ELSE 'meeting' END AS type,
       DATE '2026-11-20' - CAST(floor(random() * 45) AS INTEGER) AS activity_date
FROM accounts a, range(0, 3) g(k)
WHERE random() < 0.97""")
con.execute("""
CREATE TABLE contacts AS
SELECT 'C' || row_number() OVER () AS contact_id, a.account_id,
       CASE WHEN random() < 0.35 THEN 'Owner' ELSE 'Office Manager' END AS title
FROM accounts a, range(0, 3) g(k)
WHERE random() < 0.83""")
build_s = time.time() - t0

sizes = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ["accounts", "activities", "contacts"]}
t1 = time.time()
con.execute(open("sql/01_rules.sql").read())
rules_s = time.time() - t1
t2 = time.time()
top = con.execute("""
    SELECT owner_rep, rule, n FROM (
        SELECT owner_rep, rule, COUNT(*) n,
               ROW_NUMBER() OVER (PARTITION BY owner_rep ORDER BY COUNT(*) DESC) rk
        FROM rule_flags GROUP BY owner_rep, rule) WHERE rk = 1 ORDER BY n DESC LIMIT 3""").fetchall()
window_s = time.time() - t2
out = {"rows": sizes, "rule_breaks_found": con.execute("SELECT COUNT(*) FROM rule_flags").fetchone()[0],
       "seconds_to_build_data": round(build_s, 1), "seconds_six_rules": round(rules_s, 1),
       "seconds_scorecard_window_query": round(window_s, 2), "threads": 4}
print(json.dumps(out, indent=1))
json.dump(out, open("results_scale_test.json", "w"), indent=2)

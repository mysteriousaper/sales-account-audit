"""
Independent check of sql/05_maven_rules.sql: the same nine rules written again in plain
Python (csv module, no SQL). If both versions flag exactly the same deals, a bug in one is unlikely.
"""
import csv
import json
from datetime import date, timedelta

def load(name):
    return list(csv.DictReader(open(f"data/external/maven_crm/{name}.csv")))

deals, accounts, products, teams = load("sales_pipeline"), load("accounts"), load("products"), load("sales_teams")
acc_names = {a["account"] for a in accounts}
prices = {p["product"]: float(p["sales_price"]) for p in products}
agents = {t["sales_agent"] for t in teams}
d = lambda s: date.fromisoformat(s) if s else None
last = max(d(x["close_date"]) for x in deals if x["close_date"])

flags = set()
for x in deals:
    oid, stage = x["opportunity_id"], x["deal_stage"]
    eng, close = d(x["engage_date"]), d(x["close_date"])
    val = float(x["close_value"]) if x["close_value"] else 0.0
    if (stage in ("Won", "Lost") and close is None) or (stage in ("Prospecting", "Engaging") and close is not None):
        flags.add((oid, "M1_close_date_vs_stage"))
    if stage in ("Engaging", "Won", "Lost") and eng is None:
        flags.add((oid, "M2_missing_engage_date"))
    if close and eng and close < eng:
        flags.add((oid, "M3_closed_before_engaged"))
    if (stage == "Won" and val <= 0) or (stage == "Lost" and val != 0):
        flags.add((oid, "M4_value_vs_stage"))
    if x["product"] not in prices:
        flags.add((oid, "M5_unknown_product"))
    if stage != "Prospecting" and x["account"] not in acc_names:
        flags.add((oid, "M6_missing_or_unknown_account"))
    if stage == "Won" and x["product"] in prices and not (0.5 * prices[x["product"]] <= val <= 1.5 * prices[x["product"]]):
        flags.add((oid, "M7_price_outlier"))
    if stage == "Engaging" and eng and eng < last - timedelta(days=90):
        flags.add((oid, "M8_stale_engaging"))
    if x["sales_agent"] not in agents:
        flags.add((oid, "M9_unknown_agent"))

import duckdb
con = duckdb.connect()
for t in ["sales_pipeline", "accounts", "products", "sales_teams"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('data/external/maven_crm/{t}.csv')")
con.execute(open("sql/05_maven_rules.sql").read())
sql_flags = set(con.execute("SELECT opportunity_id, rule FROM m_flags").fetchall())
out = {"python_flags": len(flags), "sql_flags": len(sql_flags), "identical": flags == sql_flags,
       "only_in_python": len(flags - sql_flags), "only_in_sql": len(sql_flags - flags)}
print(json.dumps(out, indent=1))
json.dump(out, open("results_crosscheck.json", "w"), indent=2)

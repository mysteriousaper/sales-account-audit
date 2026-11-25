"""
Run the account audit with DuckDB, score it against the answer key,
and write results.json plus an Excel workbook for the sales managers.
"""
import json
import duckdb
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font, PatternFill

con = duckdb.connect()
for t in ["accounts", "contacts", "activities", "license_registry"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('data/{t}.csv', all_varchar=false)")
for t in ["truth_rule_violations", "truth_duplicate_contacts", "truth_duplicate_accounts"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('data/{t}.csv')")

for f in ["sql/01_rules.sql", "sql/02_dedup.sql", "sql/03_enrich.sql"]:
    con.execute(open(f).read())


def one(sql):
    return con.execute(sql).fetchone()[0]


def score(found_sql, truth_sql):
    """Precision and recall of what we flagged against the answer key."""
    tp = one(f"SELECT COUNT(*) FROM ({found_sql} INTERSECT {truth_sql})")
    found = one(f"SELECT COUNT(*) FROM ({found_sql})")
    truth = one(f"SELECT COUNT(*) FROM ({truth_sql})")
    return {"flagged": found, "seeded": truth, "correct": tp,
            "precision": round(tp / found, 4) if found else None,
            "recall": round(tp / truth, 4) if truth else None}


results = {"dataset": {
    "accounts": one("SELECT COUNT(*) FROM accounts"),
    "contacts": one("SELECT COUNT(*) FROM contacts"),
    "activities": one("SELECT COUNT(*) FROM activities"),
    "reps": one("SELECT COUNT(DISTINCT owner_rep) FROM accounts"),
    "registry_rows": one("SELECT COUNT(*) FROM license_registry")}}

results["rules_overall"] = score("SELECT account_id, rule FROM rule_flags",
                                 "SELECT account_id, rule FROM truth_rule_violations")
results["rules_by_rule"] = {}
for (rule,) in con.execute("SELECT DISTINCT rule FROM truth_rule_violations ORDER BY 1").fetchall():
    results["rules_by_rule"][rule] = score(f"SELECT account_id FROM rule_flags WHERE rule='{rule}'",
                                           f"SELECT account_id FROM truth_rule_violations WHERE rule='{rule}'")
results["accounts_failing"] = one("SELECT COUNT(DISTINCT account_id) FROM rule_flags")
results["accounts_audited"] = one("SELECT COUNT(*) FROM accounts WHERE status <> 'New'")
results["dup_contacts"] = score("SELECT contact_id_a, contact_id_b FROM dup_contacts",
                                "SELECT LEAST(contact_id_a, contact_id_b), GREATEST(contact_id_a, contact_id_b) FROM truth_duplicate_contacts")
results["dup_contacts_auto_merge"] = score("SELECT contact_id_a, contact_id_b FROM dup_contacts WHERE decision = 'auto-merge'",
                                "SELECT LEAST(contact_id_a, contact_id_b), GREATEST(contact_id_a, contact_id_b) FROM truth_duplicate_contacts")
results["dup_contacts_sent_to_review"] = one("SELECT COUNT(*) FROM dup_contacts WHERE decision = 'review'")
results["dup_accounts"] = score("SELECT account_id_a, account_id_b FROM dup_accounts",
                                "SELECT LEAST(account_id_a, account_id_b), GREATEST(account_id_a, account_id_b) FROM truth_duplicate_accounts")
results["dup_accounts_cross_rep"] = one("SELECT COUNT(*) FROM dup_accounts WHERE owner_a <> owner_b")
results["enrichment"] = {
    "accounts_missing_phone": one("SELECT COUNT(*) FROM accounts WHERE phone IS NULL OR trim(phone) = ''"),
    "phones_filled_from_registry": one("SELECT COUNT(DISTINCT account_id) FROM enrichment WHERE phone_was_missing"),
    "accounts_matched_to_license": one("SELECT COUNT(DISTINCT account_id) FROM enrichment"),
    "open_accounts_with_expired_license": one("SELECT COUNT(DISTINCT account_id) FROM enrichment WHERE license_status='Expired' "
                                              "AND status IN ('Working','Contacted','Demo Scheduled')")}

scorecard = con.execute("""
    WITH audited AS (SELECT owner_rep, account_id FROM accounts WHERE status <> 'New'),
         failing AS (SELECT DISTINCT owner_rep, account_id FROM rule_flags),
         top_rule AS (SELECT owner_rep, rule, COUNT(*) n,
                             ROW_NUMBER() OVER (PARTITION BY owner_rep ORDER BY COUNT(*) DESC, rule) rk
                      FROM rule_flags GROUP BY owner_rep, rule)
    SELECT a.owner_rep, COUNT(*) AS accounts_audited,
           COUNT(f.account_id) AS accounts_failing,
           ROUND(100.0 * COUNT(f.account_id) / COUNT(*), 1) AS fail_pct,
           MAX(t.rule) AS most_common_issue
    FROM audited a
    LEFT JOIN failing f ON f.owner_rep = a.owner_rep AND f.account_id = a.account_id
    LEFT JOIN top_rule t ON t.owner_rep = a.owner_rep AND t.rk = 1
    GROUP BY a.owner_rep ORDER BY fail_pct DESC""").fetchall()
results["rep_scorecard"] = [dict(zip(["rep", "audited", "failing", "fail_pct", "most_common_issue"], r)) for r in scorecard]

json.dump(results, open("results.json", "w"), indent=2, default=str)

# Excel workbook for managers
wb = Workbook()
head = Font(bold=True, color="FFFFFF")
fill = PatternFill("solid", fgColor="1F6F8B")


def sheet(name, header, rows):
    ws = wb.create_sheet(name)
    ws.append(header)
    for c in ws[1]:
        c.font, c.fill = head, fill
    for r in rows:
        ws.append(list(r))
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = max(12, max(len(str(c.value or "")) for c in col) + 2)
    return ws


wb.remove(wb.active)
ws = sheet("Rep scorecard", ["Rep", "Accounts audited", "Accounts failing", "Fail %", "Most common issue"], scorecard)
chart = BarChart()
chart.title = "Share of audited accounts failing at least one rule, by rep"
chart.y_axis.title = "Fail %"
chart.add_data(Reference(ws, min_col=4, min_row=1, max_row=ws.max_row), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=ws.max_row))
chart.width, chart.height = 22, 10
ws.add_chart(chart, "G2")
sheet("Flagged accounts", ["Account", "Owner rep", "Rule broken"],
      con.execute("SELECT account_id, owner_rep, rule FROM rule_flags ORDER BY owner_rep, account_id").fetchall())
sheet("Duplicate contacts", ["Contact A", "Contact B", "Account", "Why matched", "Decision"],
      con.execute("SELECT * FROM dup_contacts ORDER BY account_id").fetchall())
sheet("Duplicate accounts", ["Account A", "Account B", "Owner A", "Owner B", "Why matched"],
      con.execute("SELECT * FROM dup_accounts ORDER BY account_id_a").fetchall())
sheet("Phones from registry", ["Account", "Status", "License", "License status", "Phone was missing", "Registry phone"],
      con.execute("SELECT * FROM enrichment WHERE phone_was_missing ORDER BY account_id").fetchall())
wb.save("account_audit_results.xlsx")

print(json.dumps({k: v for k, v in results.items() if k != "rep_scorecard"}, indent=1, default=str))
print("worst rep:", scorecard[0], "best rep:", scorecard[-1])

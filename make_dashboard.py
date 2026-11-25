"""Build dashboard.html (one page for a sales manager) from results.json."""
import json

r = json.load(open("results.json"))
reps = r["rep_scorecard"]
names = {"R1_min_touches": "Fewer than 3 touches in 30 days", "R2_decision_maker": "No decision maker on file",
         "R3_next_step": "Next step missing or overdue", "R4_demo_meeting": "Demo stage without a meeting",
         "R5_dq_reason": "Disqualified without a reason", "R6_owner_mismatch": "Activity by a non-owner rep"}

bars = ""
for i, x in enumerate(reps):
    w = x["fail_pct"] * 6
    color = "#c0392b" if x["fail_pct"] >= 40 else ("#e08e0b" if x["fail_pct"] >= 20 else "#1f6f8b")
    bars += (f'<text x="0" y="{i*26+17}" class="lbl">{x["rep"]}</text>'
             f'<rect x="40" y="{i*26+4}" width="{w}" height="18" fill="{color}" rx="3"/>'
             f'<text x="{48+w}" y="{i*26+17}" class="val">{x["fail_pct"]}%  ({x["failing"]}/{x["audited"]})</text>')

rule_rows = "".join(f"<tr><td>{names[k]}</td><td>{v['flagged']}</td></tr>"
                    for k, v in sorted(r["rules_by_rule"].items(), key=lambda kv: -kv[1]["flagged"]))
worst = ", ".join(f'{x["rep"]} ({names[x["most_common_issue"]].lower()})' for x in reps[:2])

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Account audit dashboard</title>
<style>
body{{font-family:Inter,Segoe UI,Arial,sans-serif;margin:32px;color:#1b2a41;max-width:980px}}
h1{{margin:0 0 4px;font-size:24px}} .sub{{color:#5f6b77;margin-bottom:24px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}}
.kpi{{border:1px solid #dde3ea;border-radius:8px;padding:14px}} .kpi b{{font-size:26px;display:block}}
.kpi span{{color:#5f6b77;font-size:13px}} h2{{font-size:16px;margin:26px 0 10px;color:#1f6f8b}}
.lbl{{font-size:13px;fill:#1b2a41}} .val{{font-size:12px;fill:#5f6b77}}
table{{border-collapse:collapse;width:100%;font-size:14px}} td,th{{padding:7px 10px;border-bottom:1px solid #eef1f4;text-align:left}}
td:last-child,th:last-child{{text-align:right}} .note{{font-size:13px;color:#5f6b77}}
</style></head><body>
<h1>Outbound account audit</h1>
<div class="sub">Synthetic CRM export, 12 reps, audit date 2026-11-20. Built from results.json by make_dashboard.py.</div>
<div class="kpis">
<div class="kpi"><b>{r['accounts_audited']:,}</b><span>worked accounts audited</span></div>
<div class="kpi"><b>{r['accounts_failing']:,}</b><span>fail at least one rule ({round(100*r['accounts_failing']/r['accounts_audited'],1)}%)</span></div>
<div class="kpi"><b>{r['dup_accounts']['flagged']}</b><span>duplicate accounts, all owned by two reps</span></div>
<div class="kpi"><b>{r['enrichment']['phones_filled_from_registry']}</b><span>missing phones filled from the license registry</span></div>
</div>
<h2>Share of each rep's worked accounts that break at least one rule</h2>
<svg width="900" height="{len(reps)*26+6}">{bars}</svg>
<p class="note">Red 40% or more, amber 20-40%, blue under 20%. Highest: {worst}.</p>
<h2>Rule breaks by type</h2>
<table><tr><th>Rule</th><th>Accounts</th></tr>{rule_rows}</table>
<h2>Data hygiene</h2>
<table>
<tr><td>Duplicate contacts merged automatically (100% precision on the answer key)</td><td>{r['dup_contacts_auto_merge']['flagged']}</td></tr>
<tr><td>Contact pairs sent to a person for review (same email, different title and phone)</td><td>{r['dup_contacts_sent_to_review']}</td></tr>
<tr><td>Open accounts whose contractor license has expired</td><td>{r['enrichment']['open_accounts_with_expired_license']}</td></tr>
</table>
</body></html>"""
open("dashboard.html", "w").write(html)
print("dashboard.html written")

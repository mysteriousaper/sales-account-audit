"""
One command for the weekly audit: rerun every check, rebuild the dashboard and the Excel
workbook, and save a dated snapshot so each rep's failure rate can be compared week to week.
Schedule it with cron (Monday 08:00):  0 8 * * 1  cd /path/to/sales-account-audit && python run_weekly.py
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import date

steps = ["run_audit.py", "make_dashboard.py", "run_maven_audit.py"]
for s in steps:
    print("running", s)
    subprocess.run([sys.executable, s], check=True, stdout=subprocess.DEVNULL)

today = date.today().isoformat()
os.makedirs("history", exist_ok=True)
shutil.copy("results.json", f"history/results_{today}.json")

# Compare with the previous snapshot, if there is one
snaps = sorted(f for f in os.listdir("history") if f.startswith("results_"))
now = {r["rep"]: r["fail_pct"] for r in json.load(open("results.json"))["rep_scorecard"]}
if len(snaps) > 1:
    before = {r["rep"]: r["fail_pct"] for r in json.load(open("history/" + snaps[-2]))["rep_scorecard"]}
    changes = sorted(((now[k] - before.get(k, now[k]), k) for k in now), reverse=True)
    print("biggest rise in fail %:", changes[0][1], round(changes[0][0], 1))
else:
    print("first snapshot saved:", f"history/results_{today}.json")
print("done: dashboard.html, account_audit_results.xlsx, results_maven.json updated")

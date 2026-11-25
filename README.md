# Sales Account Audit

An audit of an outbound sales team's CRM: did each rep work their accounts the way the playbook says, which records are duplicates, and what a second data source can fill in. Built with SQL (DuckDB), Python and Excel. I used Claude Code to speed up the coding and checked every result against an answer key.

The data is a made-up CRM export for a team selling software to trade businesses (HVAC, plumbing, electrical, roofing). It has 12 reps, 5,110 accounts, 14,467 contacts and 15,616 logged calls, emails and meetings. Problems were seeded on purpose and recorded in an answer key (`data/truth_*.csv`). That way the audit can be scored rather than just trusted.

## What it checks

| Rule | Applies to | Requirement |
|---|---|---|
| R1 | Working, Contacted | At least 3 calls or emails in the last 30 days |
| R2 | Contacted, Demo Scheduled | A decision maker (Owner, President, GM) on file |
| R3 | All open accounts | A next step dated today or later |
| R4 | Demo Scheduled | A logged meeting |
| R5 | Disqualified | A disqualification reason |
| R6 | All | No activity logged by a rep who does not own the account |

It also finds duplicate contacts (same email, same phone plus last name, or a near-identical first name with the same last name and title) and duplicate accounts (same website after cleanup, or same company name in the same city). It then matches accounts to a public contractor-license registry to fill missing phone numbers and flag expired licenses.

## Results

- **Rule checks:** 4,308 worked accounts audited (the 802 accounts still in New status have no rules yet, so they are excluded). 1,015 of them break at least one rule, 1,165 rule breaks in total. All 1,165 seeded violations were caught, with no false flags. That is expected, since the rules were written from the playbook the data was built on. The useful part is the per-rep view.
- **Rep scorecard:** failure rates range from 9.1% (R02) to 56.8% (R08). The two weakest reps mostly miss the touch cadence (R1) or let next steps lapse (R3), which points to coaching on follow-up rather than a data problem.
- **Duplicate accounts:** 110 found, all of them created by a second rep on an account someone else already owned. Precision and recall were both 100%.
- **Duplicate contacts:** the first version matched 355 pairs with 87.6% precision. All 44 false matches had the same email but a different title and a different phone, meaning two people or a shared inbox. I split the matches into auto-merge and send-to-review. Auto-merge is now 311 pairs at 100% precision, and 44 pairs go to a person.
- **Second data source:** 355 of the 400 accounts missing a phone number were filled from the license registry. 285 open accounts belong to companies whose contractor license has expired, which reps should know before calling.

Full numbers are in `results.json`. Account-level lists and the rep chart are in `account_audit_results.xlsx`.

## Test on data I did not create

Seeded data proves little on its own, because I wrote both the errors and the checks. So I ran the same matching idea on FEBRL2, a public record-linkage benchmark from the Australian National University. It has 5,000 person records, with typos, missing values and swapped fields added by its authors, and 1,934 known duplicate pairs. Records sharing a postcode, surname or ID are compared. Each agreeing field adds points (ID 3, date of birth 2, first name, surname, address and postcode 1 each, with names and address compared using Jaro-Winkler similarity of 0.85 or more).

| Rule | Pairs flagged | Precision | Recall |
|---|---|---|---|
| Auto-merge at 4+ points | 1,883 | 100% | 97.4% |
| Review queue at exactly 3 points | 19 | 79% (15 true) | adds 0.8% |
| Combined (3+ points) | 1,902 | 99.8% | 98.1% |

To check that the 4-point threshold was not just tuned to FEBRL2, I ran it unchanged on FEBRL3, a separate file with 6,538 known duplicate pairs: 6,351 pairs auto-merged at **100% precision and 97.1% recall**, plus a review band of 59 pairs (56 true).

Run it with `pip install recordlinkage`, then `python benchmark_febrl.py` (FEBRL2, tuning) and `python holdout_febrl3.py` (FEBRL3, unseen). The data is saved in `data/external/`.

## Audit of a public CRM export (no answer key)

To test the approach on data I neither generated nor seeded, I ran a second rule set on the Maven Analytics "CRM Sales Opportunities" export. It is a public dataset for a fictitious B2B hardware seller, with 8,800 opportunities, 30 agents with deals, and 35 people on the team list. The nine rules (`sql/05_maven_rules.sql`) were written before I looked at any results.

- **2,793 of 8,800 opportunities** break at least one rule. I spot-checked 12 random flags against the raw rows, and all 12 were correct.
- **Product name mismatch:** 1,480 deals use "GTXPro", but the product list says "GTX Pro". That includes 729 won deals worth $3.51M, 35% of all won revenue ($10.01M). Any report that joins deals to the price list silently drops them. Once the name is mapped, every won deal's value is within 50-150% of list price.
- **Stale pipeline:** 1,479 of 1,589 deals in Engaging were engaged more than 90 days before the last date in the export (median age 165 days). The worst agent has 98 stale deals out of 104.
- **Missing accounts:** 1,088 of the 1,589 Engaging deals (68%) have no account attached, so nobody can tell which company the deal is with.
- **Clean areas:** close dates, engage dates, Won/Lost values and agent names all pass. Five people on the team list have no deals, and one sector is misspelled ("technolgy", 12 accounts).

**Checks on the checks:** I rewrote the nine rules in plain Python, with no SQL (`crosscheck_python.py`). Both versions flag exactly the same 4,047 rule breaks, with none in only one of them.

**Spreadsheet version:** `agent_win_rates.xlsx` (built by `build_formula_workbook.py`) holds the 8,800 raw rows and an agent summary written entirely in live formulas: COUNTIFS, SUMIFS, INDEX/MATCH and IFERROR. It shows won, lost, win rate, won revenue, average deal and open deals for each of the 30 agents, plus manager and office. It works the same in Excel and Google Sheets, and its totals (4,238 won, 2,473 lost, $10,005,534) match the SQL. Win rates run from 55% to 70%, with 63.2% overall.

Run it with `python run_maven_audit.py`. The data is in `data/external/maven_crm/`, from github.com/Shrutiijoshi/CRM-Sales-Analysis, originally Maven Analytics.

## For the sales manager

- `dashboard.html` shows headline numbers, each rep's failure rate (colour-coded) and rule breaks by type. It is built from `results.json` by `make_dashboard.py`.
- `findings_memo.md` is a one-page write-up with four findings and four recommended actions.

## Scale test

`scale_test.py` builds 1,000,000 accounts, 2.9 million activities and 2.5 million contacts inside DuckDB, then runs the same six rules from `sql/01_rules.sql`. All six rules ran in **0.9 seconds** on 4 threads, and the rep scorecard window query (`ROW_NUMBER() OVER (PARTITION BY ...)`) took 0.03 seconds. The rules are plain joins, `NOT EXISTS` checks and `GROUP BY ... HAVING`, so they port to Snowflake with only small syntax changes.

## Weekly run

`python run_weekly.py` reruns every check, rebuilds `dashboard.html` and the Excel workbook, refreshes the public-data audit, and saves a dated snapshot in `history/`. From the second week on, it prints which rep's failure rate rose most. A cron line for Monday 08:00 is in the file's header.

## Run it

```bash
pip install duckdb openpyxl
python generate_data.py   # builds data/ and the answer key
python run_audit.py       # runs sql/*.sql, scores the audit, writes results.json and the Excel file
python make_dashboard.py  # dashboard.html
python scale_test.py      # 1M-account timing test
```

## Notes for a Snowflake or Salesforce setup

The SQL is standard apart from two functions. `jaro_winkler_similarity` becomes `JAROWINKLER_SIMILARITY` in Snowflake (it returns 0-100). The `regexp_replace` flags argument also differs. The tables map to Salesforce objects: Account, Contact, and Task/Event for activities.

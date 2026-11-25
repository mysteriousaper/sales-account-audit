"""
Build agent_win_rates.xlsx on the public Maven CRM export with live spreadsheet formulas
(COUNTIFS, SUMIFS, INDEX/MATCH, IFERROR), so it works the same in Excel and Google Sheets.
Sheet "pipeline" holds the raw 8,800 rows; sheet "teams" the agent list; sheet "Agent summary" is all formulas.
"""
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
ws = wb.active
ws.title = "pipeline"
rows = list(csv.reader(open("data/external/maven_crm/sales_pipeline.csv")))
for r in rows:
    ws.append([int(x) if x.isdigit() else x for x in r])
n = len(rows)  # header + 8,800

teams = wb.create_sheet("teams")
for r in csv.reader(open("data/external/maven_crm/sales_teams.csv")):
    teams.append(r)
agents = sorted({r[1] for r in rows[1:]})

s = wb.create_sheet("Agent summary", 0)
head = ["Agent", "Manager", "Office", "Won", "Lost", "Win rate", "Won revenue", "Avg won deal", "Open (Engaging)"]
s.append(head)
for c in s[1]:
    c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F6F8B")
P = f"pipeline!$B$2:$B${n}"
STAGE = f"pipeline!$E$2:$E${n}"
VAL = f"pipeline!$H$2:$H${n}"
for i, a in enumerate(agents, start=2):
    s.append([a,
              f'=IFERROR(INDEX(teams!$B:$B,MATCH(A{i},teams!$A:$A,0)),"not on team list")',
              f'=IFERROR(INDEX(teams!$C:$C,MATCH(A{i},teams!$A:$A,0)),"")',
              f'=COUNTIFS({P},A{i},{STAGE},"Won")',
              f'=COUNTIFS({P},A{i},{STAGE},"Lost")',
              f'=IFERROR(D{i}/(D{i}+E{i}),0)',
              f'=SUMIFS({VAL},{P},A{i},{STAGE},"Won")',
              f'=IFERROR(G{i}/D{i},0)',
              f'=COUNTIFS({P},A{i},{STAGE},"Engaging")'])
    s[f"F{i}"].number_format = "0.0%"
    s[f"G{i}"].number_format = "#,##0"
    s[f"H{i}"].number_format = "#,##0"
last = len(agents) + 1
s.append(["TOTAL", "", "", f"=SUM(D2:D{last})", f"=SUM(E2:E{last})", f"=D{last+1}/(D{last+1}+E{last+1})",
          f"=SUM(G2:G{last})", f"=G{last+1}/D{last+1}", f"=SUM(I2:I{last})"])
s[f"F{last+1}"].number_format = "0.0%"
for col, w in zip("ABCDEFGHI", [20, 20, 10, 8, 8, 10, 14, 13, 15]):
    s.column_dimensions[col].width = w
wb.save("agent_win_rates.xlsx")
print("agent_win_rates.xlsx written,", len(agents), "agents")

"""Test the duplicate-matching approach on data I did not create: the FEBRL2 benchmark."""
import json
import duckdb

con = duckdb.connect()
con.execute("CREATE TABLE febrl_records AS SELECT * FROM read_csv_auto('data/external/febrl2_records.csv', all_varchar=true)")
con.execute("CREATE TABLE truth AS SELECT * FROM read_csv_auto('data/external/febrl2_true_pairs.csv')")
con.execute(open("sql/04_febrl_dedup.sql").read())
truth = con.execute("SELECT COUNT(*) FROM truth").fetchone()[0]
rows = []
for cut in range(3, 10):
    found, tp = con.execute(f"""SELECT COUNT(*), COUNT(t.rec_a) FROM febrl_matches m
        LEFT JOIN truth t ON t.rec_a = m.rec_a AND t.rec_b = m.rec_b WHERE m.points >= {cut}""").fetchone()
    rows.append({"min_points": cut, "flagged": found, "correct": tp,
                 "precision": round(tp / found, 4) if found else None, "recall": round(tp / truth, 4)})
print(json.dumps(rows, indent=1))
json.dump({"true_pairs": truth, "thresholds": rows}, open("results_febrl.json", "w"), indent=2)

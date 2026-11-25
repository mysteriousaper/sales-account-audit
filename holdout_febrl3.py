"""Check the 4-point threshold chosen on FEBRL2 on a file it never saw: FEBRL3."""
import json
import duckdb

con = duckdb.connect()
con.execute("CREATE TABLE febrl_records AS SELECT * FROM read_csv_auto('data/external/febrl3_records.csv', all_varchar=true)")
con.execute("CREATE TABLE truth AS SELECT * FROM read_csv_auto('data/external/febrl3_true_pairs.csv')")
con.execute(open("sql/04_febrl_dedup.sql").read())
truth = con.execute("SELECT COUNT(*) FROM truth").fetchone()[0]
out = {"true_pairs": truth}
for name, cond in [("auto_merge_4plus", "m.points >= 4"), ("review_band_3", "m.points = 3")]:
    found, tp = con.execute(f"""SELECT COUNT(*), COUNT(t.rec_a) FROM febrl_matches m
        LEFT JOIN truth t ON t.rec_a = m.rec_a AND t.rec_b = m.rec_b WHERE {cond}""").fetchone()
    out[name] = {"flagged": found, "correct": tp, "precision": round(tp / found, 4) if found else None,
                 "recall": round(tp / truth, 4)}
print(json.dumps(out, indent=1))
json.dump(out, open("results_febrl3_holdout.json", "w"), indent=2)

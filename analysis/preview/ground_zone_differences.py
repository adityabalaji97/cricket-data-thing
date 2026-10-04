import pandas as pd, psycopg2, numpy as np
from scipy import stats
con = psycopg2.connect("dbname=hindsight_analysis")
z = pd.read_sql("select ground, wagon_zone z, match_date from delivery_details where format='T20' and gender='male' and batruns in (4,6) and wagon_zone between 1 and 8", con)
glob = z.z.value_counts(normalize=True).sort_index()
for label, df in (("all seasons", z), ("last 4 years", z[z.match_date >= '2022-10-04'])):
    res = []
    for g, d in df.groupby("ground"):
        n = len(d)
        if n < 200: continue
        obs = d.z.value_counts().reindex(range(1, 9)).fillna(0)
        chi, p = stats.chisquare(obs, glob * n)
        ratio = (obs / n) / glob
        res.append((g, n, p, ratio.max(), int(ratio.idxmax())))
    r = pd.DataFrame(res, columns=["ground", "n", "p", "max_ratio", "zone"])
    for floor in (200, 400, 800, 1500):
        s = r[r.n >= floor]
        print(f"{label}: grounds with >= {floor} zoned boundaries: {len(s)}; differ from all grounds (p<0.01): {(s.p < 0.01).sum()}; of those with a zone at 1.25x+ its usual share: {((s.p < 0.01) & (s.max_ratio >= 1.25)).sum()}")
r = r.sort_values("p")
print(r.head(8).round(4).to_string(index=False))

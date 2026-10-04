"""
Does the way batters get out differ by ground, or is "7 in 10 wickets are catches" true everywhere?

Same test as ground_zone_differences.py: each league ground's dismissal mix (caught / bowled / lbw /
other, bowler wickets only) against all grounds, chi-square, plus the largest share ratio. Split-half
reliability (odd vs even matches) says whether a ground's mix is stable at all.
Run against hindsight_analysis (men's T20 2015+).
"""
import numpy as np
import pandas as pd
import psycopg2
from scipy import stats

con = psycopg2.connect("dbname=hindsight_analysis")
d = pd.read_sql("""
    SELECT ground, p_match, CASE WHEN dismissal = 'caught' THEN 'caught' WHEN dismissal = 'bowled' THEN 'bowled'
           WHEN dismissal = 'leg before wicket' THEN 'lbw' ELSE 'other' END AS kind
    FROM delivery_details
    WHERE format = 'T20' AND gender = 'male'
      AND dismissal IN ('caught', 'bowled', 'leg before wicket', 'stumped', 'hit wicket', 'caught and bowled')
""", con)
kinds = ["caught", "bowled", "lbw", "other"]
glob = d.kind.value_counts(normalize=True).reindex(kinds)
print("all grounds:", (glob * 100).round(1).to_dict())
rows, halves = [], []
for g, x in d.groupby("ground"):
    n = len(x)
    if n < 300:
        continue
    obs = x.kind.value_counts().reindex(kinds).fillna(0)
    chi, p = stats.chisquare(obs, glob * n)
    ratio = (obs / n) / glob
    rows.append((g, n, p, round(ratio.max(), 2), ratio.idxmax()))
    odd = x[x.p_match.astype(str).str[-1].isin(list("13579"))].kind.value_counts(normalize=True).reindex(kinds).fillna(0)
    even = x[~x.p_match.astype(str).str[-1].isin(list("13579"))].kind.value_counts(normalize=True).reindex(kinds).fillna(0)
    halves.append(((odd - glob).values, (even - glob).values))
r = pd.DataFrame(rows, columns=["ground", "wickets", "p", "max_ratio", "kind"]).sort_values("p")
a = np.concatenate([h[0] for h in halves]); b = np.concatenate([h[1] for h in halves])
print(f"grounds with 300+ bowler wickets: {len(r)}; differ (p<0.01): {(r.p < 0.01).sum()}; "
      f"and a kind at 1.25x+: {((r.p < 0.01) & (r.max_ratio >= 1.25)).sum()}")
print(f"split-half correlation of each ground's deviation from all grounds: {np.corrcoef(a, b)[0, 1]:.2f}")
print(r.head(12).round(4).to_string(index=False))

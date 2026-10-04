"""Pitch-map and boundary-zone floors for the grounds the main leagues use.

Grounds: every ground that hosted the IPL, BBL, SA20, T20 Blast, The Hundred, PSL or CPL from
2022-10-04 (the preview's default four-year window). Data: all men's T20 at those grounds.
Run against hindsight_analysis: DATABASE_URL-free, uses dbname=hindsight_analysis.

1. Coverage: per ground, pace balls with line+length and boundaries with a wagon zone, in the
   window, and how many grounds clear each candidate floor.
2. Split-half reliability (as analysis/preview/pitch_zone_reliability.py) restricted to these
   grounds: the pattern itself, and the ground's deviation from all grounds.
3. Boundary zones: grounds whose shares differ from all grounds (chi-square p < 0.01, a zone at
   1.25x+ its usual share), all seasons.
4. Bowlers in these leagues with 600+ pace balls carrying line+length (the bowler pitch-map floor).
"""
import numpy as np, pandas as pd, psycopg2
from scipy import stats

LEAGUES = ("IPL", "BBL", "BBL 2023", "SA20", "T20 Blast", "Men's Hundred", "Men's 100", "PSL", "CPL", "CPL 2023", "CPL 2024")
WINDOW = "2022-10-04"
rng = np.random.default_rng(20261004)
con = psycopg2.connect("dbname=hindsight_analysis")
grounds = pd.read_sql("select distinct ground from delivery_details where competition = any(%s) and match_date >= %s",
                      con, params=(list(LEAGUES), WINDOW)).ground.tolist()
print(f"grounds used by the leagues since {WINDOW}: {len(grounds)}")

LINES = ('DOWN_LEG', 'ON_THE_STUMPS', 'OUTSIDE_OFFSTUMP', 'WIDE_OUTSIDE_OFFSTUMP')
LENS = ('YORKER', 'FULL', 'GOOD_LENGTH', 'SHORT_OF_A_GOOD_LENGTH', 'SHORT')
pace = pd.read_sql("""select d.ground, d.p_match, d.match_date, d.line||'|'||d.length cell, -bm.raa raa
  from delivery_details d left join ball_metrics bm on bm.delivery_id = d.id
  where d.format='T20' and d.gender='male' and coalesce(d.wide,0)=0 and d.bowl_kind='pace bowler'
    and d.line = any(%s) and d.length = any(%s) and d.ground = any(%s)""", con, params=(list(LINES), list(LENS), grounds))
zones = pd.read_sql("""select ground, p_match, match_date, wagon_zone z from delivery_details
  where format='T20' and gender='male' and batruns in (4,6) and wagon_zone between 1 and 8 and ground = any(%s)""",
                    con, params=(grounds,))
zones_all = pd.read_sql("select wagon_zone z from delivery_details where format='T20' and gender='male' and batruns in (4,6) and wagon_zone between 1 and 8", con)

# 1. coverage in the window
cov = pd.DataFrame({
    "pace_ll": pace[pace.match_date >= WINDOW].groupby("ground").size(),
    "zoned_boundaries": zones[zones.match_date >= WINDOW].groupby("ground").size(),
    "zoned_boundaries_all_seasons": zones.groupby("ground").size(),
}).reindex(grounds).fillna(0).astype(int)
print("\n1. Coverage per ground in the window (pace balls with line+length / zoned boundaries)")
print(cov.describe(percentiles=[.25, .5, .75]).loc[["min", "25%", "50%", "75%", "max"]].round(0).to_string())
for f in (300, 500, 750, 1000, 1500, 2000):
    print(f"   pace balls with line+length >= {f:5d}: {(cov.pace_ll >= f).sum():3d} of {len(cov)} grounds")
for f in (200, 400, 800):
    print(f"   zoned boundaries (all seasons) >= {f:4d}: {(cov.zoned_boundaries_all_seasons >= f).sum():3d} of {len(cov)} grounds")

# 2. reliability on these grounds
cells = sorted(pace.cell.unique())
pm = pace.dropna(subset=["raa"])
glob_cell = pm.groupby("cell").raa.mean().reindex(cells) * 100
glob_zone = zones_all.z.value_counts(normalize=True).reindex(range(1, 9)).fillna(0)
pitch_vec = lambda df: (lambda g: (g["mean"] * 100).where(g["size"] >= 10))(df.groupby("cell").raa.agg(["mean", "size"]).reindex(cells))
zone_vec = lambda df: df.z.value_counts(normalize=True).reindex(range(1, 9)).fillna(0)
def corr(a, b):
    m = a.notna() & b.notna()
    return np.corrcoef(a[m], b[m])[0, 1] if m.sum() >= 5 else np.nan
def rel(df, vec, glob, n, reps=30):
    by = {m: g for m, g in df.groupby("p_match")}; ids = list(by); ra, rd = [], []
    for _ in range(reps):
        rng.shuffle(ids); take, tot = [], 0
        for m in ids:
            take.append(m); tot += len(by[m])
            if tot >= n: break
        if tot < 0.9 * n or len(take) < 4: return None
        h = rng.permutation(take); A = pd.concat([by[m] for m in h[::2]]); B = pd.concat([by[m] for m in h[1::2]])
        va, vb = vec(A), vec(B); ra.append(corr(va, vb)); rd.append(corr(va - glob, vb - glob))
    sb = lambda r: 2 * r / (1 + r)
    return sb(np.nanmean(ra)), sb(np.nanmean(rd))
print("\n2. Split-half reliability at these grounds (pattern | ground v all grounds)")
rich_p = pm.groupby("ground").size().loc[lambda s: s >= 6500].index
for n in (500, 1000, 1500, 2000, 3000):
    r = [x for x in (rel(pm[pm.ground == g], pitch_vec, glob_cell, n) for g in rich_p) if x]
    print(f"   pitch map, {n:5d} pace balls: {len(r):2d} grounds  pattern {np.nanmean([x[0] for x in r]):.2f} | vs all grounds {np.nanmean([x[1] for x in r]):.2f}")
rich_z = zones.groupby("ground").size().loc[lambda s: s >= 1700].index
for n in (200, 400, 800, 1600):
    r = [x for x in (rel(zones[zones.ground == g], zone_vec, glob_zone, n) for g in rich_z) if x]
    print(f"   zones, {n:5d} boundaries: {len(r):2d} grounds  pattern {np.nanmean([x[0] for x in r]):.2f} | vs all grounds {np.nanmean([x[1] for x in r]):.2f}")

# 3. grounds whose boundary shape differs (all seasons)
NAMES = {1: "fine leg", 2: "square leg", 3: "midwicket", 4: "long on", 5: "long off", 6: "cover", 7: "point", 8: "third man"}
res = []
for g, d in zones.groupby("ground"):
    n = len(d)
    if n < 200: continue
    obs = d.z.value_counts().reindex(range(1, 9)).fillna(0)
    p = stats.chisquare(obs, glob_zone * n).pvalue
    ratio = (obs / n) / glob_zone
    res.append((g, n, p, round(ratio.max(), 2), NAMES[int(ratio.idxmax())]))
r = pd.DataFrame(res, columns=["ground", "boundaries", "p", "ratio", "zone"])
print("\n3. Boundary shape differs from all grounds (p<0.01 and a zone at 1.25x+)")
for f in (200, 400, 800):
    s = r[r.boundaries >= f]
    print(f"   >= {f} boundaries: {len(s)} grounds, {((s.p < .01) & (s.ratio >= 1.25)).sum()} qualify")
print(r[(r.p < .01) & (r.ratio >= 1.25) & (r.boundaries >= 400)].sort_values("ratio", ascending=False).to_string(index=False))

# 4. bowlers
b = pd.read_sql("""select d.bowl, count(*) n from delivery_details d
  where d.competition = any(%s) and d.match_date >= '2024-10-04' and d.bowl_kind='pace bowler'
    and d.line = any(%s) and d.length = any(%s) group by d.bowl""", con, params=(list(LEAGUES), list(LINES), list(LENS)))
allb = pd.read_sql("""select bowl, count(*) n from delivery_details where competition = any(%s) and match_date >= '2024-10-04'
  and bowl_kind='pace bowler' group by bowl having count(*) >= 120""", con, params=(list(LEAGUES),))
m = allb.merge(b, on="bowl", how="left", suffixes=("_all", "_ll")).fillna(0)
print(f"\n4. Pace bowlers with 120+ balls in these leagues in the last 2 years: {len(m)}; with 600+ line+length balls in those leagues: {(m.n_ll >= 600).sum()}; 300+: {(m.n_ll >= 300).sum()}")

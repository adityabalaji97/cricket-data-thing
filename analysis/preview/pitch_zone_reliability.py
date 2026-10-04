"""How many balls does a ground need before its pitch map / boundary-zone pattern is stable?

Split-half reliability by subsampling matches at data-rich grounds: draw matches until the sample
holds n balls, split those matches randomly in two, compare the two halves' patterns.
  pitch map  : pace balls, 20 line x length cells, RAA per 100 (bowling view) per cell
               - absolute pattern, and the ground's deviation from the all-ground pattern
  zones      : share of boundaries in each of 8 zones (and deviation from all grounds)
Reliability of the full n = Spearman-Brown of the half-sample correlation.
"""
import numpy as np, pandas as pd, psycopg2
rng = np.random.default_rng(20261004)
con = psycopg2.connect("dbname=hindsight_analysis")
pace = pd.read_sql("""
  select d.ground, d.p_match, d.line, d.length, -bm.raa as raa
  from delivery_details d join ball_metrics bm on bm.delivery_id = d.id
  where d.format='T20' and d.gender='male' and coalesce(d.wide,0)=0
    and d.line in ('DOWN_LEG','ON_THE_STUMPS','OUTSIDE_OFFSTUMP','WIDE_OUTSIDE_OFFSTUMP')
    and d.length in ('YORKER','FULL','GOOD_LENGTH','SHORT_OF_A_GOOD_LENGTH','SHORT')
    and (d.bowl_kind='pace bowler')""", con)
zones = pd.read_sql("""
  select ground, p_match, wagon_zone as zone from delivery_details
  where format='T20' and gender='male' and batruns in (4,6) and wagon_zone between 1 and 8""", con)
print("pace balls", len(pace), "boundaries with zone", len(zones))
pace["cell"] = pace["line"] + "|" + pace["length"]
cells = sorted(pace["cell"].unique())
glob_cell = pace.groupby("cell")["raa"].mean().reindex(cells) * 100
glob_zone = zones["zone"].value_counts(normalize=True).reindex(range(1, 9)).fillna(0)

def pitch_vec(df):
    g = df.groupby("cell")["raa"].agg(["mean", "size"]).reindex(cells)
    v = g["mean"] * 100
    return v.where(g["size"] >= 10)  # cells with too few balls are not drawn

def zone_vec(df):
    return df["zone"].value_counts(normalize=True).reindex(range(1, 9)).fillna(0)

def corr(a, b):
    m = a.notna() & b.notna()
    return np.corrcoef(a[m], b[m])[0, 1] if m.sum() >= 5 else np.nan

def reliability(df, vec, glob, n, reps=40):
    by_match = {m: g for m, g in df.groupby("p_match")}
    ids = list(by_match)
    out_abs, out_dev = [], []
    for _ in range(reps):
        rng.shuffle(ids)
        take, tot = [], 0
        for m in ids:
            take.append(m); tot += len(by_match[m])
            if tot >= n: break
        if tot < n * 0.9 or len(take) < 4: return None
        half = rng.permutation(take); a, b = half[::2], half[1::2]
        va = vec(pd.concat([by_match[m] for m in a])); vb = vec(pd.concat([by_match[m] for m in b]))
        out_abs.append(corr(va, vb)); out_dev.append(corr(va - glob, vb - glob))
    sb = lambda r: 2 * r / (1 + r) if r == r else np.nan
    return sb(np.nanmean(out_abs)), sb(np.nanmean(out_dev))

rows = []
rich_p = pace.groupby("ground").size().loc[lambda s: s >= 9000].index
rich_z = zones.groupby("ground").size().loc[lambda s: s >= 2500].index
print("rich grounds: pitch", len(rich_p), "zones", len(rich_z))
for n in (250, 500, 1000, 1500, 2000, 3000, 4000, 6000):
    res = [reliability(pace[pace.ground == g], pitch_vec, glob_cell, n) for g in rich_p]
    res = [r for r in res if r]
    rows.append(("pitch (pace balls)", n, len(res), np.nanmean([r[0] for r in res]), np.nanmean([r[1] for r in res])))
for n in (50, 100, 200, 400, 800, 1200, 2000):
    res = [reliability(zones[zones.ground == g], zone_vec, glob_zone, n) for g in rich_z]
    res = [r for r in res if r]
    rows.append(("zones (boundaries)", n, len(res), np.nanmean([r[0] for r in res]), np.nanmean([r[1] for r in res])))
t = pd.DataFrame(rows, columns=["card", "n", "grounds", "rel_pattern", "rel_vs_all_grounds"])
print(t.round(2).to_string(index=False))
t.to_csv("analysis/preview/reliability.csv", index=False)

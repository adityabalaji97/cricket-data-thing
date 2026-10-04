import numpy as np, pandas as pd, psycopg2
rng = np.random.default_rng(7)
con = psycopg2.connect("dbname=hindsight_analysis")
pace = pd.read_sql("""select d.bowl, d.ground, d.p_match, d.line||'|'||d.length cell, -bm.raa raa from delivery_details d join ball_metrics bm on bm.delivery_id=d.id
  where d.format='T20' and d.gender='male' and coalesce(d.wide,0)=0 and d.bowl_kind='pace bowler'
  and d.line in ('DOWN_LEG','ON_THE_STUMPS','OUTSIDE_OFFSTUMP','WIDE_OUTSIDE_OFFSTUMP') and d.length in ('YORKER','FULL','GOOD_LENGTH','SHORT_OF_A_GOOD_LENGTH','SHORT')""", con)
cells = sorted(pace.cell.unique())
# usage share per cell is what a bowler's pitch map mostly shows ("where he bowls"); and RAA per cell
glob_use = pace.cell.value_counts(normalize=True).reindex(cells)
glob_raa = pace.groupby("cell").raa.mean().reindex(cells) * 100
def use_vec(df): return df.cell.value_counts(normalize=True).reindex(cells).fillna(0)
def raa_vec(df):
    g = df.groupby("cell").raa.agg(["mean", "size"]).reindex(cells); return (g["mean"] * 100).where(g["size"] >= 10)
def corr(a, b):
    m = a.notna() & b.notna(); return np.corrcoef(a[m], b[m])[0, 1] if m.sum() >= 5 else np.nan
sb = lambda r: 2 * r / (1 + r)
rich = pace.groupby("bowl").size().loc[lambda s: s >= 4000].index
print("bowlers", len(rich))
for n in (300, 600, 1000, 2000):
    u, r = [], []
    for b in rich:
        df = pace[pace.bowl == b]; by = {m: g for m, g in df.groupby("p_match")}; ids = list(by)
        for _ in range(20):
            rng.shuffle(ids); take, tot = [], 0
            for m in ids:
                take.append(m); tot += len(by[m])
                if tot >= n: break
            h = rng.permutation(take); A = pd.concat([by[m] for m in h[::2]]); B = pd.concat([by[m] for m in h[1::2]])
            u.append(corr(use_vec(A) - glob_use, use_vec(B) - glob_use)); r.append(corr(raa_vec(A) - glob_raa, raa_vec(B) - glob_raa))
    print(f"bowler n={n}: where he bowls vs average {sb(np.nanmean(u)):.2f} | runs saved by cell vs average {sb(np.nanmean(r)):.2f}")
z = pd.read_sql("select ground, wagon_zone z from delivery_details where format='T20' and gender='male' and batruns in (4,6) and wagon_zone between 1 and 8", con)
g = z.z.value_counts(normalize=True).sort_index(); w = z[z.ground.str.startswith('Wankhede')].z.value_counts(normalize=True).sort_index()
print(pd.DataFrame({"all grounds %": (100*g).round(1), "Wankhede %": (100*w).round(1)}).T.to_string())

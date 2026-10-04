"""
How big are real batter-v-bowler edges? Sets the shrinkage for the Key Battles card (D1).

For every IPL pair since 2018 with 18+ balls: edge = the pair's RAA per 100 minus (the batter's RAA
per 100 against everyone + the bowler's RAA per 100 conceded to everyone). The observed spread of
edges is true spread plus noise; noise per pair is 162 / sqrt(balls) per 100 (per-ball RAA sd 1.62,
ball_metrics). True spread = sqrt(observed variance - mean noise variance).

Result (2026-10-04, hindsight_analysis): 1,929 pairs, observed sd 35.0, noise sd 31.7, true sd 14.8
runs per 100. So k = 162^2 / 14.8^2 ~ 120 balls: a pair's likely edge is its raw edge x n / (n + 120).
"""
import statistics as st
from datetime import date

from database import SessionLocal
from services.query_builder_v2 import _run_deliveries_query_uncached as q

db = SessionLocal()
W = dict(fmt="T20", gender="male", leagues=["IPL"], start_date=date(2018, 1, 1), end_date=date.today(),
         metrics_perspective="batting", limit=100000)
pairs = q(db, group_by=["batter", "bowler"], min_balls=18, **W)["data"]
bat = {r["batter"]: r for r in q(db, group_by=["batter"], **W)["data"]}
bowl = {r["bowler"]: r for r in q(db, group_by=["bowler"], **W)["data"]}
edges, noise = [], []
for r in pairs:
    b, w = bat.get(r["batter"]), bowl.get(r["bowler"])
    if r.get("raa_per_100") is None or not b or not w:
        continue
    edges.append(r["raa_per_100"] - (b["raa_per_100"] or 0) - (w["raa_per_100"] or 0))
    noise.append(162 ** 2 / (r.get("metric_balls") or r["balls"]))
true_var = max(st.pvariance(edges) - st.mean(noise), 0)
print(f"pairs {len(edges)}; observed sd {st.pvariance(edges) ** .5:.1f}; noise sd {st.mean(noise) ** .5:.1f}; "
      f"true sd {true_var ** .5:.1f}; k = {162 ** 2 / true_var:.0f} balls")

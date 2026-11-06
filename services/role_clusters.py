"""
Roles as the data sees them (TEAM_TEMPLATE_PLAN.md, T2): every player-season's usage, clustered per league, each cluster
described and named after its nearest familiar role, so the phase x job labels are checked against how teams actually
use players rather than assumed.

Usage vector (shares, so a part-timer and a regular with the same job sit together; volume separately):
  batting  - share of the side's balls he faced; his balls by position slot (1-2, 3-4, 5-7, 8+) and by phase;
  bowling  - share of the side's balls he bowled; his balls by phase; his share bowled as spin.
"""
from __future__ import annotations

from typing import Any, Dict, List

from services.team_roles import BAT_SLOTS, PHASES, bat_slot

MIN_BALLS = 60
SLOTS = [s for s, _, _ in BAT_SLOTS]


def usage_vectors(league_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for s in league_data["seasons"]:
        for team, players in s["teams"].items():
            tb = sum((r.get("balls") or 0) for p in players for r in p["bat"].values()) or 1
            tw = sum((r.get("balls") or 0) for p in players for r in p["bowl"].values()) or 1
            for p in players:
                bb = sum((r.get("balls") or 0) for r in p["bat"].values())
                wb = sum((r.get("balls") or 0) for r in p["bowl"].values())
                if bb < MIN_BALLS and wb < MIN_BALLS:
                    continue
                v = {"bat_volume": bb / tb, "bowl_volume": wb / tw}
                for slot in SLOTS:
                    v[f"pos_{slot}"] = sum((r.get("balls") or 0) for pos, r in p["bat"].items() if bat_slot(int(pos)) == slot) / bb if bb else 0
                for ph in PHASES:
                    v[f"batphase_{ph}"] = ((p["bat_phase"].get(ph) or {}).get("balls") or 0) / bb if bb else 0
                    v[f"bowlphase_{ph}"] = sum((r.get("balls") or 0) for k, r in p["bowl"].items() if k.startswith(ph + "|")) / wb if wb else 0
                v["spin"] = sum((r.get("balls") or 0) for k, r in p["bowl"].items() if k.endswith("|spin")) / wb if wb else 0
                out.append({"season": s["season"], "team": team, "name": p["name"], "bat_balls": bb, "bowl_balls": wb,
                            "playoff": team in s["playoff"], "vector": v})
    return out


BAT_KEYS = ["bat_volume"] + [f"pos_{s}" for s in SLOTS] + [f"batphase_{p}" for p in PHASES]
BOWL_KEYS = ["bowl_volume"] + [f"bowlphase_{p}" for p in PHASES] + ["spin"]


def describe(c: Dict[str, float], side: str) -> str:
    """A familiar name for a cluster centre."""
    if side == "bat":
        slot = max(SLOTS, key=lambda s_: c[f"pos_{s_}"])
        name = {"openers": "Opener", "top": "Top order (3-4)", "middle": "Middle order (5-7)", "lower": "Lower order (8+)"}[slot]
        if slot == "middle" and c["batphase_death"] > 0.4:
            name = "Finisher (5-7, death-heavy)"
        if c[f"pos_{slot}"] < 0.6:
            second = sorted(SLOTS, key=lambda s_: -c[f"pos_{s_}"])[1]
            name += f" / floats to {dict(openers='1-2', top='3-4', middle='5-7', lower='8+')[second]}"
        return name
    kind = "Spin" if c["spin"] > 0.5 else "Pace"
    order = sorted(PHASES, key=lambda p: -c[f"bowlphase_{p}"])
    tag = {"powerplay": "powerplay", "middle": "middle overs", "death": "death"}
    if c[f"bowlphase_{order[0]}"] < 0.45:
        return f"{kind}, all phases"
    return f"{kind}, {tag[order[0]]}" + (f" + {tag[order[1]]}" if c[f"bowlphase_{order[1]}"] > 0.28 else "")


def cluster(league_data: Dict[str, Any], side: str, k: int, seed: int = 7) -> Dict[str, Any]:
    """Cluster the batting (side="bat") or bowling ("bowl") of every player-season with 60+ balls of it."""
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    keys = BAT_KEYS if side == "bat" else BOWL_KEYS
    vs = [v for v in usage_vectors(league_data) if v["bat_balls" if side == "bat" else "bowl_balls"] >= MIN_BALLS]
    X = np.array([[v["vector"][k_] for k_ in keys] for v in vs])
    Xs = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=k, n_init=20, random_state=seed).fit(Xs)
    from sklearn.metrics import silhouette_score
    clusters = []
    for i in range(k):
        idx = [j for j, l in enumerate(km.labels_) if l == i]
        centre = {key: float(X[idx, n].mean()) for n, key in enumerate(keys)}
        members = [vs[j] for j in idx]
        examples = sorted(members, key=lambda m: -(m["bat_balls"] if side == "bat" else m["bowl_balls"]))[:6]
        clusters.append({"id": i, "label": describe(centre, side), "size": len(idx), "centre": centre,
                         "playoff_share": sum(m["playoff"] for m in members) / len(members),
                         "examples": [f"{m['name']} ({m['team']} {m['season']})" for m in examples]})
    for j, v in enumerate(vs):
        v["cluster"] = int(km.labels_[j])
    return {"side": side, "keys": keys, "silhouette": float(silhouette_score(Xs, km.labels_)),
            "clusters": sorted(clusters, key=lambda c: -c["size"]), "players": vs}

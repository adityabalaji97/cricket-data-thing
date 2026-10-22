"""
Players by ESPNcricinfo id (PLAYER_IDS_PLAN.md). delivery_details names each ball's batter and bowler and carries
their ids (p_bat, p_bowl); names collide, ids don't. build() gives every id one display name and stores it in
player_identity: where ids share a (canonical) name, the id with the most balls keeps the name and the others carry
their main side, "Rohit Sharma (Indonesia)". Spelling variants (one id, several names) resolve through the alias map
first, so they stay one player. Balls with no id (the legacy pre-2015 table) go by name to that name's main player.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from sqlalchemy import text


def compute(db) -> List[Dict]:
    """Every id's row for player_identity: {pid, display_name, name, main_side, balls, first_date, last_date}."""
    from services.competition_normalizer import international_competitions
    from services.player_aliases import ALIAS_MAP_CTE

    rows = db.execute(text(f"""
        WITH {ALIAS_MAP_CTE}, b AS (
            SELECT dd.p_bat AS pid, COALESCE(am.canonical_name, dd.bat) AS name, dd.team_bat AS team,
                   (m.match_type = 'international' AND m.competition = ANY(:intl)) AS intl, m.date
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
            LEFT JOIN alias_map am ON LOWER(dd.bat) = am.name_key
            WHERE dd.p_bat IS NOT NULL AND dd.bat IS NOT NULL
            UNION ALL
            SELECT dd.p_bowl, COALESCE(am.canonical_name, dd.bowl), dd.team_bowl,
                   (m.match_type = 'international' AND m.competition = ANY(:intl)), m.date
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
            LEFT JOIN alias_map am ON LOWER(dd.bowl) = am.name_key
            WHERE dd.p_bowl IS NOT NULL AND dd.bowl IS NOT NULL
        )
        SELECT pid, name, team, intl, COUNT(*) AS n, MIN(date) AS first, MAX(date) AS last FROM b GROUP BY 1, 2, 3, 4
    """), {"intl": list(set(international_competitions("T20")) | set(international_competitions("ODI")))}).all()
    names: Dict[int, Dict[str, int]] = {}
    sides: Dict[int, Dict[Tuple[str, bool], int]] = {}
    span: Dict[int, List] = {}
    for pid, name, team, intl, n, first, last in rows:
        ns, ts = names.setdefault(pid, {}), sides.setdefault(pid, {})
        ns[name] = ns.get(name, 0) + n
        ts[(team, bool(intl))] = ts.get((team, bool(intl)), 0) + n
        s = span.setdefault(pid, [first, last])
        s[0], s[1] = min(s[0], first), max(s[1], last)

    def main_side(pid: int) -> str:
        t = sides[pid]
        national = {k: v for k, v in t.items() if k[1]}
        pool = national or t
        return max(pool, key=pool.get)[0]

    canonical = {pid: max(ns, key=ns.get) for pid, ns in names.items()}
    balls = {pid: sum(ns.values()) for pid, ns in names.items()}
    by_name: Dict[str, List[int]] = {}
    for pid, name in canonical.items():
        by_name.setdefault(name, []).append(pid)
    out, taken = [], set()
    for name, pids in by_name.items():
        pids.sort(key=lambda p: (-balls[p], p))
        for i, p in enumerate(pids):
            display = name if i == 0 else f"{name} ({main_side(p)})"
            k = 2
            while display in taken:  # two namesakes from one side: number them
                display = f"{name} ({main_side(p)} {k})"
                k += 1
            taken.add(display)
            out.append({"pid": p, "display_name": display, "name": name, "main_side": main_side(p), "balls": balls[p],
                        "first_date": span[p][0], "last_date": span[p][1]})
    return out


def build(db) -> Dict[str, int]:
    """Rebuild player_identity in one transaction (readers see the old table until it commits)."""
    rows = compute(db)
    db.execute(text("DELETE FROM player_identity"))
    # One statement from arrays: ~30k rows one INSERT at a time took over ten minutes to Heroku (a round trip each).
    cols = ("pid", "display_name", "name", "main_side", "balls", "first_date", "last_date")
    db.execute(text("""
        INSERT INTO player_identity (pid, display_name, name, main_side, balls, first_date, last_date)
        SELECT * FROM unnest(CAST(:pid AS bigint[]), CAST(:display_name AS text[]), CAST(:name AS text[]),
                             CAST(:main_side AS text[]), CAST(:balls AS int[]), CAST(:first_date AS date[]),
                             CAST(:last_date AS date[]))
    """), {c: [r[c] for r in rows] for c in cols})
    db.commit()
    return {"players": len(rows), "namesakes": sum(1 for r in rows if r["display_name"] != r["name"])}


def load(db) -> Tuple[Dict[int, str], Dict[str, str]]:
    """({pid: display name}, {name: display name of its main player}) from the stored table."""
    rows = db.execute(text("SELECT pid, display_name, name FROM player_identity")).all()
    display = {r[0]: r[1] for r in rows}
    main = {r[2]: r[2] for r in rows}
    return display, main


def namesakes(db, top: int = 50) -> List[Dict]:
    """The namesakes with the most balls, for the one-off review: every id behind each shared name."""
    return [dict(r) for r in db.execute(text("""
        SELECT name, display_name, pid, main_side, balls, first_date, last_date FROM player_identity
        WHERE name IN (SELECT name FROM player_identity GROUP BY name HAVING COUNT(*) > 1)
        ORDER BY (SELECT MAX(balls) FROM player_identity p2 WHERE p2.name = player_identity.name) DESC, name, balls DESC
        LIMIT :n
    """), {"n": top}).mappings().all()]

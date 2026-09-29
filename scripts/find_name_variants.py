"""
Report likely spelling variants of the same player in delivery_details (read-only).

A feed that changes how it spells a player ("Vaibhav Suryavanshi" -> "Vaibhav Sooryavanshi")
splits their record in two unless player_aliases links the spellings. Candidates here:
  - same first name (or matching initial), surnames at least 75% similar;
  - played for at least one common team;
  - never both appear in the same match (two people can; one person cannot);
  - not already aliased to the same canonical name.
Prints evidence per pair; applying aliases is a separate, reviewed step.

    python scripts/find_name_variants.py [--min-similarity 0.75] [--json out.json]
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from database import get_session  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-similarity", type=float, default=0.75)
    parser.add_argument("--json", default=None)
    args = parser.parse_args()
    db = next(get_session())

    rows = db.execute(text("""
        SELECT name, team, COUNT(*) AS balls, MIN(match_date) AS first, MAX(match_date) AS last,
               COUNT(DISTINCT p_match) AS matches
        FROM (
            SELECT bat AS name, team_bat AS team, match_date, p_match FROM delivery_details
            UNION ALL
            SELECT bowl, team_bowl, match_date, p_match FROM delivery_details
        ) x
        WHERE name IS NOT NULL
        GROUP BY name, team
    """)).mappings().all()
    players = defaultdict(lambda: {"teams": set(), "balls": 0, "first": "9999", "last": "0000", "matches": 0})
    for r in rows:
        p = players[r["name"]]
        p["teams"].add(r["team"])
        p["balls"] += r["balls"]
        p["matches"] += r["matches"]
        p["first"] = min(p["first"], r["first"] or "9999")
        p["last"] = max(p["last"], r["last"] or "0000")

    canon = dict(db.execute(text("""
        SELECT LOWER(player_name), alias_name FROM player_aliases
        UNION ALL SELECT LOWER(alias_name), alias_name FROM player_aliases
    """)).all())

    blocks = defaultdict(list)
    for name in players:
        tokens = norm(name).split()
        if len(tokens) < 2:
            continue
        blocks[(tokens[0][:1], tokens[-1][:1])].append(name)

    candidates = []
    for names in blocks.values():
        for i, a in enumerate(names):
            ta = norm(a).split()
            for b in names[i + 1:]:
                tb = norm(b).split()
                first_ok = ta[0] == tb[0] or (len(ta[0]) <= 2 or len(tb[0]) <= 2) and ta[0][0] == tb[0][0]
                if not first_ok:
                    continue
                sim = SequenceMatcher(None, ta[-1], tb[-1]).ratio()
                if sim < args.min_similarity or a.lower() == b.lower():
                    continue
                if not (players[a]["teams"] & players[b]["teams"]):
                    continue
                ca, cb = canon.get(a.lower(), a), canon.get(b.lower(), b)
                if ca == cb:
                    continue
                candidates.append((a, b, sim))

    report = []
    for a, b, sim in candidates:
        together = db.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT p_match FROM delivery_details WHERE bat = :a OR bowl = :a OR non_striker = :a
                INTERSECT
                SELECT p_match FROM delivery_details WHERE bat = :b OR bowl = :b OR non_striker = :b
            ) t
        """), {"a": a, "b": b}).scalar()
        if together:
            continue
        pa, pb = players[a], players[b]
        report.append({
            "names": [a, b], "surname_similarity": round(sim, 2),
            "shared_teams": sorted(pa["teams"] & pb["teams"]),
            a: {"balls": pa["balls"], "matches": pa["matches"], "span": f"{pa['first']}..{pa['last']}"},
            b: {"balls": pb["balls"], "matches": pb["matches"], "span": f"{pb['first']}..{pb['last']}"},
            "existing_canonical": {a: canon.get(a.lower()), b: canon.get(b.lower())},
        })
    report.sort(key=lambda r: -sum(v["balls"] for k, v in r.items() if k in r["names"]))
    for r in report:
        a, b = r["names"]
        print(f"{a!r:32} {r[a]['span']:24} {r[a]['balls']:>6}b | {b!r:32} {r[b]['span']:24} {r[b]['balls']:>6}b "
              f"| sim {r['surname_similarity']} | {', '.join(r['shared_teams'])[:60]}")
    print(f"\n{len(report)} candidate pairs", file=sys.stderr)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

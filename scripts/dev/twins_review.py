"""
The statistical twins review list (DOPPELGANGER_PLAN.md S3): career "plays like" twins and a cross-era season twin
for 40 players the user knows, written to docs/twins_review.md. Reads player_vectors directly (no web requests).

    python scripts/dev/twins_review.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("USAGE_LOGGING", "0")

PLAYERS = [
    "Abhishek Sharma", "Vaibhav Sooryavanshi", "Shubman Gill", "Yashasvi Jaiswal", "Suryakumar Yadav", "Tilak Varma",
    "Hardik Pandya", "Rinku Singh", "Sanju Samson", "Virat Kohli", "Rohit Sharma", "Jasprit Bumrah", "Arshdeep Singh",
    "Kuldeep Yadav", "Varun Chakaravarthy", "Axar Patel", "Shivam Dube", "Heinrich Klaasen", "Travis Head",
    "Rashid Khan", "Sunil Narine", "Andre Russell", "Jos Buttler", "Phil Salt", "Nicholas Pooran", "Mitchell Starc",
    "Pat Cummins", "Trent Boult", "Kagiso Rabada", "Marco Jansen", "Aiden Markram", "David Miller", "Glenn Maxwell",
    "Tristan Stubbs", "Shaheen Shah Afridi", "Babar Azam", "Mitchell Santner", "Rachin Ravindra", "Noor Ahmad",
    "Wanindu Hasaranga",
]


def main() -> int:
    from database import get_session
    from services.twins import twins_for

    db = next(get_session())
    out = ["# Statistical twins review (S3)", "",
           "\"Plays like\" twins from production. Careers: the profile's window (since Jan 2024, major leagues + top-12",
           "T20Is). Season: the player's 2025 against every season since 2015. Gap: typical percentile-point difference",
           "across the features compared (lower is closer). Mark any twin that looks wrong to a cricket eye.", "",
           "| Player | Role | Career twins (gap) | 2025 cross-era twins (gap) | Same (closest twin) |",
           "|---|---|---|---|---|"]
    for name in PLAYERS:
        c = twins_for(db, name, "window", n=3)
        s = twins_for(db, name, "season", "2025", n=3)
        if not c.get("qualified"):
            out.append(f"| {name} | – | not in the pool | | |")
            continue
        careers = "; ".join(f"{t['player']} ({t['gap_points']})" for t in c["twins"])
        seasons = "; ".join(f"{t['player']} {t['period']} ({t['gap_points']})" for t in s.get("twins", [])) or "–"
        same = ", ".join(x["label"] for x in (c["twins"][0]["closest"] if c["twins"] else []))
        out.append(f"| {c['player']} | {c['role']} | {careers} | {seasons} | {same} |")
        print(f"{c['player']:22s} {c['role']:9s} {careers}")
    Path("docs/twins_review.md").write_text("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
IPL auction history (migration 038): every lot from Cricbuzz's auction pages (data/auction_raw, 2018-26 complete,
2008-17 the top 20 lots a year), matched to our players, for the profile's "IPL auctions" card and posts.

    load(db, raw_dir)          parse the CSVs, match names (services/name_match.py), replace both tables
    history(db, player)        a player's lots, newest first, with his bid count
"""
from __future__ import annotations

import csv
import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)

STATUS = {"sold", "unsold", "retained", "rtm", "traded", "drafted", "replacement"}
# A franchise's code in the auction files -> its name in ours (renamed sides keep their own name).
TEAMS = {"MI": "Mumbai Indians", "CSK": "Chennai Super Kings", "RCB": "Royal Challengers Bengaluru",
         "KKR": "Kolkata Knight Riders", "SRH": "Sunrisers Hyderabad", "RR": "Rajasthan Royals", "DC": "Delhi Capitals",
         "PBKS": "Punjab Kings", "GT": "Gujarat Titans", "LSG": "Lucknow Super Giants", "KXIP": "Kings XI Punjab",
         "DD": "Delhi Daredevils", "DCG": "Deccan Chargers", "RPSG": "Rising Pune Supergiant", "PWI": "Pune Warriors",
         "GL": "Gujarat Lions", "KTK": "Kochi Tuskers Kerala"}


# Reviewed by hand (10 Nov 2026): auction spellings the matcher misses or gets wrong. None: no player of ours.
OVERRIDES = {
    "Lokesh Rahul": "KL Rahul", "Nitish Reddy": "Nitish Kumar Reddy", "Allah Ghazanfar": "AM Ghazanfar",
    "Mujeeb Zadran": "Mujeeb Ur Rahman", "K Khaleel Ahmed": "Khaleel Ahmed", "N Jagadeesan": "Narayan Jagadeesan",
    "Arshad Khan": "Arshad Khan (Gujarat Titans)", "Mohd Arshad Khan": "Arshad Khan (Gujarat Titans)",
    "Rasikh Salam": "Rasikh Dar", "Digvesh Singh": "Digvesh Rathi", "Daniel Christian": "Dan Christian",
    "Simran Singh": "Prabhsimran Singh", "Manvinder Bisla": "Manvinder Bisla",
    # Near-names that are other people.
    "Jitender Pal": None, "Avinash Singh": None, "Pratyush Singh": None, "Chintal Gandhi": None,
}
CLEAN = "regexp_replace(regexp_replace(display_name, E'\\u00a0', ' ', 'g'), ' {2,}', ' ', 'g')"


def lakh(v: Optional[str]) -> Optional[float]:
    """'2.00 Cr' -> 200.0, '30.00 L' -> 30.0, '--' or '' -> None."""
    v = (v or "").strip()
    try:
        if v.endswith("Cr"):
            return round(float(v[:-2]) * 100, 2)
        if v.endswith("L"):
            return round(float(v[:-1]), 2)
    except ValueError:
        pass
    return None


def _active(db, year: int):  # db: the session players are matched in
    """A candidate must have played around the auction (any T20 from three years before to a year after), so a
    namesake from another era isn't matched."""
    def ok(display_name: str) -> bool:
        r = db.execute(text("SELECT first_date, last_date FROM player_identity WHERE display_name = :n"),
                       {"n": display_name}).fetchone()
        if not r or not r[0]:
            return False
        return r[0] <= date(year + 1, 12, 31) and r[1] >= date(year - 3, 1, 1)
    return ok


def load(db, raw_dir: Path, tournament: str = "ipl", match_db=None) -> Dict[str, Any]:
    """Replace the tournament's lots and bids in `db`. `match_db`: where players are matched, when not `db` (a local
    load matched against production's full player list, read-only)."""
    from services.name_match import match_display_name

    mdb = match_db or db
    lots, bids, matched = [], [], {}
    for f in sorted((raw_dir / tournament).glob("*/completed_all_players.csv")):
        for r in csv.DictReader(open(f)):
            status = (r.get("auctionStatus") or "").strip().lower()
            if status not in STATUS:
                continue
            year, cb = int(r["year"]), int(r["playerId"])
            key = (r["playerName"], year)
            if key not in matched:
                raw = " ".join(r["playerName"].replace("\xa0", " ").split())
                dn = OVERRIDES[raw] if raw in OVERRIDES else match_display_name(mdb, raw, accept=_active(mdb, year))
                matched[key] = mdb.execute(text(f"SELECT pid FROM player_identity WHERE {CLEAN} = :n"),
                                          {"n": dn}).scalar() if dn else None
            lots.append({"t": tournament, "y": year, "cb": cb, "name": r["playerName"].replace("\xa0", " ").strip(),
                         "pid": matched[key], "country": r.get("country") or None, "role": r.get("role") or None,
                         "status": status, "team": (r.get("playsForTeam") or "").strip() or None,
                         "base": lakh(r.get("basePrice")), "price": lakh(r.get("auctionPrice")),
                         "capped": (r.get("cappedStatus") or "").upper() == "CAPPED",
                         "overseas": (r.get("isPlayerOverseas") or "") == "True",
                         "nbids": int(r["trail_bid_count"]) if (r.get("trail_bid_count") or "").isdigit() else None})
        trail = f.parent / "completed_trail.csv"
        if trail.exists():
            by: Dict[tuple, list] = {}
            for r in csv.DictReader(open(trail)):
                by.setdefault((int(r["year"]), int(r["playerId"])), []).append(r)
            for (year, cb), rs in by.items():
                rs.sort(key=lambda r: int(r["seq"]))  # seq 1 is the winning bid
                n = len(rs)
                bids += [{"t": tournament, "y": year, "cb": cb, "no": n - i, "team": r.get("team") or None,
                          "price": lakh(r.get("price"))} for i, r in enumerate(rs)]
    db.execute(text("DELETE FROM auction_bids WHERE tournament = :t"), {"t": tournament})
    db.execute(text("DELETE FROM auction_lots WHERE tournament = :t"), {"t": tournament})
    db.execute(text("""
        INSERT INTO auction_lots (tournament, year, cb_player_id, player_name, pid, country, role, status, team,
                                  base_lakh, price_lakh, capped, overseas, bids)
        VALUES (:t, :y, :cb, :name, :pid, :country, :role, :status, :team, :base, :price, :capped, :overseas, :nbids)
        ON CONFLICT DO NOTHING"""), lots)
    if bids:
        db.execute(text("""INSERT INTO auction_bids (tournament, year, cb_player_id, bid_no, team, price_lakh)
                           VALUES (:t, :y, :cb, :no, :team, :price) ON CONFLICT DO NOTHING"""), bids)
    db.commit()
    unmatched = sorted({(n, y) for (n, y), pid in matched.items() if pid is None}, key=lambda x: (-x[1], x[0]))
    return {"lots": len(lots), "bids": len(bids), "players": len(matched), "unmatched": unmatched}


def history(db, player: str) -> List[Dict[str, Any]]:
    """His IPL auction lots, newest first: year, status, team, prices (lakh) and how many bids his lot drew."""
    from services.query_builder_v2 import _player_ids

    pids = _player_ids([player], db) or []
    if not pids:
        return []
    rows = db.execute(text("""
        SELECT year, status, team, base_lakh, price_lakh, bids FROM auction_lots
        WHERE tournament = 'ipl' AND pid = ANY(:p) ORDER BY year DESC"""), {"p": pids}).fetchall()
    return [{"year": y, "status": s, "team": t, "team_name": TEAMS.get(t or ""), "base_lakh": float(b) if b is not None else None,
             "price_lakh": float(p) if p is not None else None, "bids": n} for y, s, t, b, p, n in rows]

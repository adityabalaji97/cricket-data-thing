"""
Season running tallies for leagues in progress (Notes plan §C.3): the recurring posts that work on
r/Cricket ("Playoff Probabilities & Impact of X vs Y", 550-670 upvotes a post).

  playoffs   the points table from results so far, and each side's chance of finishing in the
             playoff places, from 20,000 simulations of the remaining league fixtures with each
             match's win probability from Elo
  impact     the season's batting and bowling Impact leaders, as query-builder charts

Both become content packs in the Social queue on a cadence (a new playoff table every 7 league
matches, new Impact leaders every 10), so a league gets a steady weekly-ish series.

The schedule (which matches are league stage, what is left) comes from ESPN's league scoreboard:
its calendar lists every match day and each event's description says "30th Match" or
"Qualifier 1". ESPN event ids are the same cricinfo ids as matches.id. Results are Hindsight's;
a match ESPN has finished but the nightly load has not reached yet counts from ESPN's winner flag,
so the table is never a day behind.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from services import content_rules
from services.competition_aliases import canonical_competition, variants_for

logger = logging.getLogger(__name__)

# ESPN league ids. Others are learnt from the live header feed while their season runs and kept in
# app_meta ("espn_league:<label>"), since a league only appears there on match days.
KNOWN_ESPN_LEAGUES = {"IPL": 8048}
PRIMER_LEAGUES = content_rules.MAIN_LEAGUES - {"Men's Hundred"}   # no Impact for the Hundred
PLAYOFF_SPOTS = {"Men's Hundred": 3}
POINTS_WIN, POINTS_NO_RESULT = 2, 1
SIMULATIONS = 20000
NRR_NOISE = 0.25            # simulated net run rates drift this much (sd) by the end of a league
PLAYOFF_WORDS = re.compile(r"qualifier|eliminator|final|playoff|play-off|knockout|challenger|semi", re.I)
PLAYOFF_EVERY, IMPACT_EVERY = 7, 10      # league matches between packs
MIN_PLAYED = 10
ACTIVE_DAYS = 10
ESPN = "https://site.web.api.espn.com/apis/site/v2/sports/cricket"
HEADER = "https://site.api.espn.com/apis/personalized/v2/scoreboard/header?sport=cricket&region=in&lang=en"
UA = {"User-Agent": "Mozilla/5.0 (compatible; CricketDataThing/1.0)", "Accept": "application/json"}


def _get(url: str, attempts: int = 3) -> Optional[Dict[str, Any]]:
    """GET JSON; ESPN's edge often answers 502/504 once and then fine, so retry with a short backoff."""
    import time

    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers=UA), timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            if attempt == attempts - 1:
                logger.warning("ESPN fetch failed (%s): %s", url, exc)
            else:
                time.sleep(1.5 * (attempt + 1))
    return None


class ScheduleIncomplete(RuntimeError):
    """A match day could not be fetched: odds from a partial fixture list would be wrong."""


# ------------------------------------------------------------------------------------- schedule

def espn_league_id(db: Session, label: str) -> Optional[int]:
    """The league's ESPN id: remembered, known, or found in today's header feed."""
    key = f"espn_league:{label}"
    stored = db.execute(text("SELECT value FROM app_meta WHERE key = :k"), {"k": key}).scalar()
    if stored:
        return int(stored)
    found = None
    for sport in (_get(HEADER) or {}).get("sports") or []:
        for league in sport.get("leagues") or []:
            if canonical_competition(league.get("name") or "") == label:
                found = int(league["id"])
    found = found or KNOWN_ESPN_LEAGUES.get(label)
    if found:
        from database import engine

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO app_meta (key, value) VALUES (:k, :v)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
            """), {"k": key, "v": str(found)})
    return found


def _event(e: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    comp = (e.get("competitions") or [{}])[0]
    teams = [(c.get("team") or {}).get("displayName") for c in comp.get("competitors") or []]
    if len(teams) != 2 or not all(teams):
        return None
    winner = next(((c.get("team") or {}).get("displayName") for c in comp.get("competitors") or []
                   if str(c.get("winner")).lower() == "true"), None)
    if not winner:
        # A tie settled by a Super Over: "Match tied (KKR won the Super Over)". Neither ESPN's winner
        # flag nor matches.winner records it, but the points go to that side.
        tied = re.search(r"\((.+?) won (?:the )?(?:super over|one-over eliminator)", str((e.get("status") or {}).get("summary") or ""), re.I)
        if tied:
            abbr = {((c.get("team") or {}).get("abbreviation") or "").upper(): (c.get("team") or {}).get("displayName")
                    for c in comp.get("competitors") or []}
            winner = abbr.get(tied.group(1).strip().upper()) or next((t for t in teams if t.lower() == tied.group(1).strip().lower()), None)
    description = e.get("description") or comp.get("description") or ""
    return {"id": str(e.get("id")), "date": (e.get("date") or "")[:10], "team1": teams[0], "team2": teams[1],
            "description": description, "playoff": bool(PLAYOFF_WORDS.search(description.split(",")[0])),
            "state": ((e.get("status") or {}).get("type") or {}).get("state"), "winner": winner,
            "season": (e.get("season") or {}).get("year")}


def season_schedule(league_id: int) -> List[Dict[str, Any]]:
    """Every match of the league's current (or latest) season, from its calendar of match days."""
    head = _get(f"{ESPN}/{league_id}/scoreboard")
    if not head:
        return []
    from concurrent.futures import ThreadPoolExecutor

    calendar = ((head.get("leagues") or [{}])[0].get("calendar") or [])
    urls = [f"{ESPN}/{league_id}/scoreboard?dates={day[:10].replace('-', '')}" for day in calendar]
    with ThreadPoolExecutor(max_workers=6) as pool:
        pages = list(pool.map(_get, urls))
    missing = [u.rsplit("=", 1)[1] for u, page in zip(urls, pages) if page is None]
    if missing:
        raise ScheduleIncomplete(f"could not fetch match days {', '.join(missing)}")
    events: Dict[str, Dict[str, Any]] = {}
    for page in pages:
        for e in page.get("events") or []:
            ev = _event(e)
            if ev:
                events[ev["id"]] = ev
    return sorted(events.values(), key=lambda e: (e["date"], e["id"]))


# ------------------------------------------------------------------------------------- table

def _results(db: Session, ids: List[str]) -> Dict[str, Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT id, team1, team2, COALESCE(winner, outcome->>'eliminator') AS winner FROM matches WHERE id = ANY(:ids)
    """), {"ids": ids}).mappings()
    return {str(r["id"]): dict(r) for r in rows}


def _innings_totals(db: Session, ids: List[str]) -> Dict[Tuple[str, str], Tuple[int, int]]:
    """{(match_id, team): (runs, balls)} for net run rate, from ball-by-ball data. A side bowled out
    is charged its full quota of balls, as the NRR rules do."""
    rows = db.execute(text("""
        SELECT dd.p_match AS m, dd.team_bat AS team, MAX(dd.inns_runs) AS runs, MAX(dd.inns_balls) AS balls,
               MAX(dd.inns_wkts) AS wkts, MAX(dd.max_balls) AS quota
        FROM delivery_details dd WHERE dd.p_match = ANY(:ids) AND dd.inns IN (1, 2)
        GROUP BY 1, 2
    """), {"ids": ids}).mappings()
    out = {}
    for r in rows:
        balls = r["quota"] if (r["wkts"] or 0) >= 10 and r["quota"] else r["balls"]
        out[(str(r["m"]), r["team"])] = (int(r["runs"] or 0), int(balls or 0))
    return out


def points_table(db: Session, schedule: List[Dict[str, Any]], as_of: Optional[date] = None) -> Dict[str, Any]:
    """League-stage table from results, and the fixtures still to play.

    `as_of` replays a past season: matches on or after it count as unplayed.
    """
    league = [e for e in schedule if not e["playoff"]]
    teams = sorted({t for e in league for t in (e["team1"], e["team2"])})
    stored = _results(db, [e["id"] for e in league])
    table = {t: {"team": t, "played": 0, "won": 0, "lost": 0, "nr": 0, "points": 0, "for": [0, 0], "against": [0, 0]}
             for t in teams}
    played_ids, remaining = [], []
    for e in league:
        before = as_of is None or date.fromisoformat(e["date"]) < as_of
        row = stored.get(e["id"])
        winner = (row["winner"] if row else None) or (e["winner"] if e["state"] == "post" else None)
        finished = before and (row is not None or e["state"] == "post")
        if not finished:
            remaining.append((e["team1"], e["team2"]))
            continue
        played_ids.append(e["id"])
        for t in (e["team1"], e["team2"]):
            table[t]["played"] += 1
        if winner in (e["team1"], e["team2"]):
            loser = e["team2"] if winner == e["team1"] else e["team1"]
            table[winner]["won"] += 1
            table[winner]["points"] += POINTS_WIN
            table[loser]["lost"] += 1
        else:
            for t in (e["team1"], e["team2"]):
                table[t]["nr"] += 1
                table[t]["points"] += POINTS_NO_RESULT
    totals = _innings_totals(db, played_ids)
    by_match = defaultdict(dict)
    for (m, team), v in totals.items():
        by_match[m][team] = v
    for m, sides in by_match.items():
        if len(sides) != 2:
            continue
        (a, va), (b, vb) = sides.items()
        for t, mine, theirs in ((a, va, vb), (b, vb, va)):
            if t in table:
                table[t]["for"][0] += mine[0]; table[t]["for"][1] += mine[1]
                table[t]["against"][0] += theirs[0]; table[t]["against"][1] += theirs[1]
    for row in table.values():
        f, a = row.pop("for"), row.pop("against")
        row["nrr"] = round((f[0] / f[1] - a[0] / a[1]) * 6, 3) if f[1] and a[1] else 0.0
    return {"table": list(table.values()), "remaining": remaining, "played": len(played_ids),
            "start": date.fromisoformat(league[0]["date"]) if league else None}


# ------------------------------------------------------------------------------------- simulation

def win_probability(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))


def simulate(table: List[Dict[str, Any]], remaining: List[Tuple[str, str]], elos: Dict[str, float], spots: int,
             sims: int = SIMULATIONS, seed: int = 7) -> Dict[str, Dict[str, float]]:
    """Chance of finishing in the top `spots` (and top 2) for each team; points, then NRR, decide places."""
    rng = np.random.default_rng(seed)
    teams = [r["team"] for r in table]
    index = {t: i for i, t in enumerate(teams)}
    points = np.tile(np.array([r["points"] for r in table], dtype=float), (sims, 1))
    if remaining:
        a = np.array([index[x] for x, _ in remaining])
        b = np.array([index[y] for _, y in remaining])
        p = np.array([win_probability(elos[x], elos[y]) for x, y in remaining])
        a_wins = rng.random((sims, len(remaining))) < p
        np.add.at(points, (np.arange(sims)[:, None], np.where(a_wins, a, b)), POINTS_WIN)
    nrr = np.array([r["nrr"] for r in table]) + rng.normal(0, NRR_NOISE, (sims, len(teams)))
    # Rank by points, then NRR (a tiny NRR term never outweighs one point).
    order = np.argsort(-(points * 1000 + nrr), axis=1)
    place = np.empty_like(order)
    np.put_along_axis(place, order, np.arange(len(teams))[None, :].repeat(sims, 0), axis=1)
    return {t: {"top": float((place[:, i] < spots).mean()), "top2": float((place[:, i] < 2).mean())}
            for t, i in index.items()}


def _pct(p: float) -> str:
    """Display a probability honestly at the extremes: '>99%' / '<1%' rather than 100 / 0."""
    if p >= 0.995:
        return ">99%" if p < 1.0 else "100%"
    if p <= 0.005:
        return "<1%" if p > 0.0 else "0%"
    return f"{round(p * 100)}%"


def _pct_number(p: float) -> int:
    return 99 if 0.995 <= p < 1.0 else 1 if 0.0 < p <= 0.005 else round(p * 100)


# ------------------------------------------------------------------------------------- packs

def season_label(league: str, start: date, end: date) -> str:
    return f"{league} {start.year}" if start.year == end.year else f"{league} {start.year}-{str(end.year)[2:]}"


def playoff_fact(db: Session, league: str, schedule: List[Dict[str, Any]], as_of: Optional[date] = None) -> Optional[Dict[str, Any]]:
    from services.match_preview import _get_latest_elo

    state = points_table(db, schedule, as_of)
    if state["played"] < MIN_PLAYED or not state["remaining"]:
        return None
    spots = PLAYOFF_SPOTS.get(league, 4)
    elos = {r["team"]: float(_get_latest_elo(db, r["team"], before=as_of) or 1500) for r in state["table"]}
    probs = simulate(state["table"], state["remaining"], elos, spots)
    rows = sorted(state["table"], key=lambda r: (-probs[r["team"]]["top"], -r["points"], -r["nrr"]))
    end = date.fromisoformat(schedule[-1]["date"])
    label = season_label(league, state["start"], end)
    top, bottom = rows[0], rows[-1]
    pt, pb = probs[top["team"]]["top"], probs[bottom["team"]]["top"]
    tail = f"{bottom['team']} can no longer qualify" if pb == 0 else f"{bottom['team']} are down to {_pct(pb)}"
    title = f"{top['team']} are {_pct(pt)} to make the {label} playoffs after {state['played']} matches; {tail}"
    year = state["start"].year
    numbers = {"top_pct": _pct_number(pt), "bottom_pct": _pct_number(pb), "played": state["played"], "year": year,
               "end_year": int(str(end.year)[2:]), "spots": spots}
    chart_rows = [{"rank": i + 1, "label": r["team"], "pct": round(probs[r["team"]]["top"] * 100, 1),
                   "display": f"{_pct(probs[r['team']]['top'])} · {r['points']} pts", "highlight": False}
                  for i, r in enumerate(rows)]
    method = (f"Chance of a top-{spots} finish from {SIMULATIONS:,} simulations of the {len(state['remaining'])} league "
              f"matches left, each side's win probability from its Elo rating; points, then net run rate, decide places. "
              f"Results to {as_of or date.today():%d %b %Y}.")
    return {"kind": "season_playoffs", "subject": top["team"], "team": top["team"], "title": title, "numbers": numbers,
            "method": method, "scope": label, "since_year": year, "played": state["played"],
            "table": [{**r, **{k: round(v, 4) for k, v in probs[r["team"]].items()}} for r in rows],
            "chart": {"metric": "pct", "group": "teams", "rows": chart_rows, "metric_label": f"chance of top {spots}"}}


def impact_facts(db: Session, league: str, start: date, label: str, played: int) -> List[Dict[str, Any]]:
    """Batting and bowling Impact leaders this season, as query snapshots (live query-builder charts)."""
    from services.snapshots import SnapshotError, create_snapshot

    if league not in PRIMER_LEAGUES:
        return []
    games_each = max(1, round(played * 2 / 10))
    facts = []
    for side, group, min_balls in (("batting", "batter", max(30, 8 * games_each)),
                                   ("bowling", "bowler", max(24, 6 * games_each))):
        params = {"leagues": [league], "fmt": "T20", "gender": "male", "start_date": start.isoformat(),
                  "group_by": [group], "min_balls": min_balls, "sort_by": "impact", "limit": 8}
        try:
            snap = create_snapshot(db, "query", params, created_by="tallies")
        except SnapshotError as exc:
            logger.info("no %s Impact chart for %s: %s", side, label, exc)
            continue
        rows = [r for r in (snap.get("data") or {}).get("rows") or [] if isinstance(r.get("impact"), (int, float))]
        if len(rows) < 3:
            continue
        top = rows[0]
        runs = round(top["impact"])
        title = (f"{top[group]} leads {label} {side} Impact after {played} matches with "
                 + (f"+{runs} runs added" if side == "batting" else f"{runs} runs saved"))
        snap = create_snapshot(db, "query", {**params, "title": title}, created_by="tallies")
        facts.append({
            "kind": f"season_impact_{side}", "subject": top[group], "team": None, "title": title,
            "numbers": {"impact": runs, "played": played, "year": start.year, "balls": min_balls},
            "method": (f"Impact: runs a {'batter added to' if side == 'batting' else 'bowler saved from'} the batting side's "
                       f"projected total, ball by ball (Ganjoo's T20 Primer). {label} so far, {min_balls}+ balls."),
            "scope": label, "since_year": start.year, "snapshot_id": snap["id"], "played": played,
        })
    return facts


def _save_pack(db: Session, league: str, fact: Dict[str, Any], angle_key: str, snapshot_id: str, link_path: str,
               dry_run: bool) -> Dict[str, Any]:
    errors, warnings = content_rules.check_title(fact["title"], [fact["numbers"]], fact["subject"])
    if errors:
        return {"angle_key": angle_key, "title": fact["title"], "refused": errors}
    routing = content_rules.route({"competition": league}, fact)
    pack = {"angle_key": angle_key, "title": fact["title"], "subreddit": routing["subreddit"], "flair": routing["flair"],
            "rule_warnings": warnings}
    if dry_run:
        return pack
    link = content_rules.tracked_url(link_path, f"pack-{snapshot_id}")
    comment = "\n\n".join([fact["method"], f"The season's ball-by-ball numbers: {link}",
                           "Data: Hindsight (hindsightcricket.com), a free cricket stats site."])
    stored = {k: v for k, v in fact.items() if k not in ("chart",)}
    stored["alternates"] = routing["alternates"]
    from database import engine

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO content_packs (match_id, snapshot_id, angle_key, title, first_comment, subreddit, flair,
                                       facts, rule_warnings, status, post_by, source)
            VALUES (NULL, :s, :k, :t, :c, :sub, :fl, CAST(:facts AS jsonb), CAST(:w AS jsonb), 'ready', :pb, 'tally')
            ON CONFLICT (angle_key) WHERE angle_key IS NOT NULL DO NOTHING RETURNING id
        """), {"s": snapshot_id, "k": angle_key, "t": fact["title"], "c": comment, "sub": routing["subreddit"],
               "fl": routing["flair"], "facts": json.dumps(stored, default=str), "w": json.dumps(warnings),
               "pb": content_rules.post_by(date.today())}).first()
    pack.update(id=row[0] if row else None, snapshot_id=snapshot_id, duplicate=row is None)
    return pack


def _playoff_chart_data(fact: Dict[str, Any]) -> Dict[str, Any]:
    spots = fact["numbers"]["spots"]
    return {
        "title": fact["title"], "kicker": f"{fact['scope']} · playoff race", "subtitle": fact["method"],
        "filter_chips": [fact["scope"], f"top {spots} qualify"], "group_by": ["team"], "query_mode": "ranking",
        "columns": ["rank", "label", "pct", "display"], "metric_columns": ["pct"], "metric_label": f"chance of top {spots}",
        "rows": fact["chart"]["rows"], "chart": {"type": "bar", "label_key": "label", "metric": "pct"},
        "row_limit": len(fact["chart"]["rows"]), "note": fact["method"],
        "source": f"{fact['scope']} · results to date · Elo · Hindsight",
    }


def _season_query(league: str, year: int, start: str, group: str) -> str:
    """The season in the query builder: the first comment's link."""
    return "/query?" + urlencode([("leagues", league), ("start_date", start), ("group_by", group), ("fmt", "mens-t20")])


def active_leagues(db: Session, today: Optional[date] = None) -> List[str]:
    """Main leagues with a match loaded in the last ACTIVE_DAYS days."""
    today = today or date.today()
    rows = db.execute(text("SELECT DISTINCT competition FROM matches WHERE date >= :d AND gender = 'male'"),
                      {"d": today - timedelta(days=ACTIVE_DAYS)}).scalars()
    return sorted({canonical_competition(c) for c in rows} & content_rules.MAIN_LEAGUES)


def generate(db: Session, leagues: Optional[List[str]] = None, dry_run: bool = False,
             as_of: Optional[date] = None) -> Dict[str, Any]:
    """Playoff-race and Impact-leader packs for each league in season, on their cadence."""
    from services.snapshots import create_static_snapshot

    summary: Dict[str, Any] = {"leagues": [], "packs": [], "refused": [], "skipped": []}
    for league in leagues or active_leagues(db):
        league_id = espn_league_id(db, league)
        if not league_id:
            summary["skipped"].append(f"{league}: no ESPN league id yet")
            continue
        try:
            schedule = season_schedule(league_id)
        except ScheduleIncomplete as exc:
            summary["skipped"].append(f"{league}: {exc}")
            continue
        if not schedule:
            summary["skipped"].append(f"{league}: no schedule from ESPN")
            continue
        summary["leagues"].append(league)
        fact = playoff_fact(db, league, schedule, as_of)
        if fact:
            season_key = f"{league}:{fact['since_year']}"
            angle = f"tally:{season_key}:playoffs:{fact['played'] // PLAYOFF_EVERY}"
            snap = None if dry_run else create_static_snapshot(db, "ranking", _playoff_chart_data(fact), fact["title"],
                                                               {"tally": angle}, created_by="tallies")
            pack = _save_pack(db, league, fact, angle, snap["id"] if snap else "", _season_query(league, fact["since_year"],
                              next(e["date"] for e in schedule if not e["playoff"]), "batting_team"), dry_run)
            (summary["refused"] if pack.get("refused") else summary["packs"]).append({**pack, "table": fact["table"]})
            label, played, start = fact["scope"], fact["played"], date.fromisoformat(
                next(e["date"] for e in schedule if not e["playoff"]))
        else:
            state = points_table(db, schedule, as_of)
            if not state["start"] or state["played"] < MIN_PLAYED:
                summary["skipped"].append(f"{league}: {state['played']} league matches played")
                continue
            start, played = state["start"], state["played"]
            label = season_label(league, start, date.fromisoformat(schedule[-1]["date"]))
        for f in ([] if dry_run else impact_facts(db, league, start, label, played)):
            angle = f"tally:{league}:{start.year}:{f['kind']}:{played // IMPACT_EVERY}"
            path = _season_query(league, start.year, start.isoformat(), "batter" if "batting" in f["kind"] else "bowler")
            pack = _save_pack(db, league, f, angle, f["snapshot_id"], path, dry_run)
            (summary["refused"] if pack.get("refused") else summary["packs"]).append(pack)
    return summary

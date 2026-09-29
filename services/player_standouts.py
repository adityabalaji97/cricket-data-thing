"""
"What stands out" for a player: short facts written from their stats patterns
(services.player_patterns) and T20 Primer metrics by season, ranked by Jev for how distinctive
they are. Code formats every number; Jev only orders. Without Jev the order is fixed by kind.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.fact_curation import score_facts, top

STANDOUT_CRITERIA = [
    "Generic: true of most players in this role; says nothing distinctive",
    "Descriptive: a fair summary of how they play, but not notable",
    "Notable: a clear strength, weakness or trend a knowledgeable fan would point out",
    "Striking: among the first things an analyst would say about this player right now",
    "Defining: the single most distinctive thing about this player's recent cricket",
]
# Fallback order without Jev: recent value first, then style.
KIND_ORDER = ["impact_latest", "impact_trend", "rank", "raa", "wpa", "matchup_best", "pace_spin",
              "style", "phase", "matchup_worst", "position", "usage"]
MIN_RANK_BALLS = {"batting": 300, "bowling": 240}
_RANK_CACHE: Dict[tuple, Dict[str, int]] = {}
COMBO_LABELS = {"lhb_lhb": "two left-handers", "lhb_rhb": "a left-right pair", "rhb_rhb": "two right-handers"}


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _poss(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _signed(x: float, digits: int = 1) -> str:
    return f"{'+' if x >= 0 else '-'}{abs(x):.{digits}f}"


def impact_by_year(db: Session, names: List[str], role: str, years: int = 3) -> List[Dict[str, Any]]:
    col, sign = ("dd.bat", 1) if role == "batting" else ("dd.bowl", -1)
    rows = db.execute(text(f"""
        SELECT LEFT(dd.match_date, 4) AS year, COUNT(DISTINCT dd.p_match) AS innings, COUNT(*) AS balls,
               {sign} * SUM(bm.impact::double precision) AS impact,
               {sign} * SUM(bm.raa::double precision) AS raa,
               {sign} * SUM(bm.wpa::double precision) AS wpa
        FROM delivery_details dd
        JOIN ball_metrics bm ON bm.delivery_id = dd.id
        JOIN matches m ON m.id = dd.p_match
        WHERE {col} = ANY(:names) AND COALESCE(dd.wide, 0) = 0 AND m.format = 'T20' AND m.gender = 'male'
        GROUP BY 1 ORDER BY 1 DESC LIMIT :years
    """), {"names": names, "years": years}).mappings().all()
    return [dict(r) for r in rows]


def impact_rank(db: Session, name_set: List[str], role: str, year: str) -> Optional[Dict[str, int]]:
    """Rank by total Impact among men's T20 players with enough balls that year (cached per year)."""
    key = (role, year)
    if key not in _RANK_CACHE:
        col, sign = ("dd.bat", 1) if role == "batting" else ("dd.bowl", -1)
        rows = db.execute(text(f"""
            SELECT {col} AS player, {sign} * SUM(bm.impact::double precision) AS impact
            FROM delivery_details dd
            JOIN ball_metrics bm ON bm.delivery_id = dd.id
            JOIN matches m ON m.id = dd.p_match
            WHERE dd.match_date LIKE :year AND COALESCE(dd.wide, 0) = 0 AND m.format = 'T20' AND m.gender = 'male'
            GROUP BY 1 HAVING COUNT(*) >= :min_balls
            ORDER BY 2 DESC
        """), {"year": f"{year}%", "min_balls": MIN_RANK_BALLS[role]}).mappings().all()
        _RANK_CACHE[key] = {r["player"]: i for i, r in enumerate(rows, 1)} | {"__total__": len(rows)}
    ranks = _RANK_CACHE[key]
    rank = next((ranks[n] for n in name_set if n in ranks), None)
    return {"rank": rank, "of": ranks["__total__"]} if rank else None


def _fact(facts: List[Dict[str, Any]], kind: str, text_: str) -> None:
    facts.append({"id": f"s{len(facts)}", "kind": kind, "text": text_})


def _impact_facts(facts, name: str, role: str, years: List[Dict[str, Any]], rank: Optional[Dict[str, int]]) -> None:
    if not years or (years[0]["balls"] or 0) < 60:
        return
    latest = years[0]
    verb = "added" if role == "batting" else "saved"
    per = latest["impact"] / max(1, latest["innings"])
    _fact(facts, "impact_latest", f"In {latest['year']}, {name} {verb} {latest['impact']:.1f} runs through {role} "
          f"(Impact) in {latest['innings']} innings, {_signed(per)} a game." if latest["impact"] >= 0 else
          f"In {latest['year']}, {_poss(name)} {role} cost {abs(latest['impact']):.1f} runs against expected (Impact) "
          f"in {latest['innings']} innings.")
    if rank:
        _fact(facts, "rank", f"That {role} Impact ranks {_ordinal(rank['rank'])} of {rank['of']} men's T20 "
              f"{'batters' if role == 'batting' else 'bowlers'} with {MIN_RANK_BALLS[role]}+ balls in {latest['year']}.")
    if len(years) > 1 and (years[1]["balls"] or 0) >= 60:
        prev = years[1]
        prev_per = prev["impact"] / max(1, prev["innings"])
        direction = "up" if per > prev_per else "down"
        _fact(facts, "impact_trend", f"{_poss(name)} {role} Impact per innings is {_signed(per)} in {latest['year']}, "
              f"{direction} from {_signed(prev_per)} in {prev['year']}.")
    if role == "batting":
        _fact(facts, "raa", f"In {latest['year']}, {name} scored {_signed(latest['raa'])} runs above an average batter "
              f"in the same match situations (RAA).")
    _fact(facts, "wpa", f"{_poss(name)} {role} added {_signed(latest['wpa'], 2)} wins in {latest['year']} (win probability added).")


def build_batter_facts(name: str, patterns: Dict[str, Any], years: List[Dict[str, Any]], rank) -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []
    _impact_facts(facts, name, "batting", years, rank)
    sr, bp = patterns.get("overall_strike_rate"), patterns.get("overall_boundary_percentage")
    if sr and bp is not None:
        _fact(facts, "style", f"Strike rate {sr:.0f} in this window, with {bp:.0f}% of balls hit for four or six.")
    phase = patterns.get("primary_phase")
    share = (patterns.get("phase_distribution") or {}).get(phase)
    if phase and isinstance(share, (int, float)):
        _fact(facts, "phase", f"{share:.0f}% of {_poss(name)} balls come in the {phase if phase != 'middle' else 'middle overs'}.")
    pace_sr, spin_sr = patterns.get("pace_sr"), patterns.get("spin_sr")
    if pace_sr and spin_sr and abs(pace_sr - spin_sr) >= 15:
        _fact(facts, "pace_spin", f"Strike rate {spin_sr:.0f} against spin and {pace_sr:.0f} against pace.")
    for kind, key, label in (("matchup_best", "strengths", "Best"), ("matchup_worst", "weaknesses", "Weakest")):
        item = (patterns.get(key) or [None])[0]
        if item and item.get("balls", 0) >= 30:
            _fact(facts, kind, f"{label} matchup: {item['context']}, strike rate {item['strike_rate']:.0f} and average "
                  f"{item['average']:.1f} over {item['balls']} balls.")
    pos = patterns.get("typical_batting_position")
    if pos:
        _fact(facts, "position", f"Usually bats at number {pos}.")
    return facts


def build_bowler_facts(name: str, patterns: Dict[str, Any], years: List[Dict[str, Any]], rank) -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []
    _impact_facts(facts, name, "bowling", years, rank)
    econ, bsr, dots = patterns.get("overall_economy"), patterns.get("overall_strike_rate"), patterns.get("overall_dot_percentage")
    if econ and bsr and dots is not None:
        _fact(facts, "style", f"Economy {econ:.2f} in this window, a wicket every {bsr:.0f} balls, {dots:.0f}% dot balls.")
    dist = patterns.get("phase_distribution") or {}
    phases = [(p, d) for p, d in dist.items() if isinstance(d, dict) and d.get("overs")]
    if phases:
        p, d = max(phases, key=lambda x: x[1].get("overs_percentage", 0))
        _fact(facts, "phase", f"{d['overs_percentage']:.0f}% of {_poss(name)} overs come in the "
              f"{p if p != 'middle' else 'middle overs'}, at {d['economy']:.2f} an over.")
    for kind, key in (("matchup_best", "best_crease_combo"), ("matchup_worst", "worst_crease_combo")):
        combo = patterns.get(key) or {}
        if combo.get("balls", 0) >= 30 and combo.get("combo") in COMBO_LABELS:
            label = "Best" if kind == "matchup_best" else "Most expensive"
            _fact(facts, kind, f"{label} against {COMBO_LABELS[combo['combo']]} at the crease: economy {combo['economy']:.2f}, "
                  f"{combo.get('wickets', 0)} wickets in {combo['balls']} balls.")
    over, pct = patterns.get("primary_over"), patterns.get("primary_over_percentage")
    if over and pct:
        _fact(facts, "usage", f"Most often bowls over {over}, in {pct:.0f}% of matches.")
    return facts


def standouts(db: Session, role: str, display_name: str, names: List[str], patterns: Dict[str, Any]) -> Dict[str, Any]:
    years = impact_by_year(db, names, role)
    rank = impact_rank(db, names, role, years[0]["year"]) if years and years[0]["balls"] >= MIN_RANK_BALLS[role] else None
    builder = build_batter_facts if role == "batting" else build_bowler_facts
    facts = builder(display_name, patterns, years, rank)
    if not facts:
        return {"available": False}
    state = {"player": display_name, "role": role,
             "task": "Each candidate is a verified fact about this T20 player. Judge how distinctive it is."}
    jev = score_facts(facts, state, "How much does this fact stand out about this player?", STANDOUT_CRITERIA)
    if not jev:
        for f in facts:
            f["score"] = len(KIND_ORDER) - KIND_ORDER.index(f["kind"]) if f["kind"] in KIND_ORDER else 0
    chosen = top(facts, 4, threshold=2.0 if jev else 0.0)
    return {
        "available": True,
        "source": "typed" if jev else "deterministic",
        "headline": chosen[0]["text"],
        "bullets": [f["text"] for f in chosen[1:]],
    }

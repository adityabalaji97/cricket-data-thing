"""
Questions worth a carousel: generated from templates x scopes, kept only when the data can't settle them in one
number, ranked by how much fans would argue about them.

  1. Candidates: who is the best {role} {situation} in {scope}? (players of spin, finishers, death bowlers, new-ball
     bowlers, chasers, the most complete partnership...), each with the query-builder filters that define it.
  2. Contested: the planner picks the question's angles; the question is kept when those angles have at least
     MIN_LEADERS different leaders. One player leading on everything is a fact, not a debate.
  3. Appeal: Jev scores how much Instagram cricket fans would argue about each kept question (without Jev, the
     template's own priority).

Nothing here writes a number: the question text names no result, and its answer is the post's cards.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services import jev_client
from services.ig_posts import angles as A
from services.ig_posts.context import QuestionContext
from services.ig_posts.planner import plan

MIN_LEADERS = 2
APPEAL_CRITERIA = [
    "Dull: nobody would comment",
    "Mild: a few fans of these teams might reply",
    "Talking point: fans would share an opinion",
    "Debate: fans would argue in the comments",
    "Flashpoint: everyone has a take and would share it",
]


@dataclass
class Question:
    key: str
    text: str            # the hook: a question, no result in it
    role: str            # batter | bowler | partnership
    fmt: str
    params: Dict[str, Any]
    min_balls: int
    scope_label: str     # "IPL since 2023 · 150+ balls in overs 16-20"
    kicker: str          # "IPL" / "T20Is" / "ODIs"
    priority: int = 2    # template priority (0..4), the fallback for Jev's appeal score
    subject: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    noun: str = ""       # "finisher", "player of spin": how search titles name the role (services/search_titles)


# Scopes: (key, hook phrase, sample label, kicker, fmt, params). T20Is and ODIs keep to matches between the top 10
# teams so associates don't lead; the hook stays short and the sample line says so.
T20_SCOPES = [
    ("ipl23", "in the IPL since 2023", "IPL since 2023", "IPL", "T20", {"leagues": ["IPL"], "start_date": "2023-01-01"}),
    ("t20i23", "in T20Is since 2023", "T20Is between the top 10 since 2023", "T20Is", "T20",
     {"include_international": True, "top_teams": 10, "start_date": "2023-01-01"}),
]
# ODIs since the 2023 World Cup (the final was 19 Nov 2023): the cycle that leads to the 2027 World Cup.
ODI_SINCE = "2023-11-20"
ODI_SCOPES = [
    ("odiwc", "in ODIs since the 2023 World Cup", "ODIs between the top 10 since the 2023 World Cup", "ODIs", "ODI",
     {"include_international": True, "top_teams": 10, "start_date": ODI_SINCE}),
]

# Situations: (key, noun for the question, filters, min balls by scope key, priority, roles)
BATTER_SITUATIONS = [
    ("spin", "player of spin", {"bowl_kind": ["spin bowler"]}, {"ipl23": 250, "t20i23": 150, "odiwc": 300}, 4),
    ("pace", "player of pace", {"bowl_kind": ["pace bowler"]}, {"ipl23": 400, "t20i23": 250, "odiwc": 500}, 3),
    ("pp", "powerplay batter", {"over_min": 0, "over_max": 5}, {"ipl23": 250, "t20i23": 150}, 3),
    ("odi_pp", "new-ball batter", {"over_min": 0, "over_max": 9}, {"odiwc": 250}, 3),
    ("death", "finisher", {"over_min": 15, "over_max": 19}, {"ipl23": 120, "t20i23": 80}, 4),
    ("odi_death", "finisher", {"over_min": 40, "over_max": 49}, {"odiwc": 120}, 3),
    ("middle", "middle-overs batter", {"over_min": 6, "over_max": 14}, {"ipl23": 300, "t20i23": 200}, 2),
    ("chase", "chaser", {"is_chase": True}, {"ipl23": 400, "t20i23": 250, "odiwc": 400}, 4),
    ("all", "batter", {}, {"ipl23": 700, "t20i23": 400, "odiwc": 800}, 3),
]
BOWLER_SITUATIONS = [
    ("pp", "new-ball bowler", {"over_min": 0, "over_max": 5}, {"ipl23": 240, "t20i23": 150}, 4),
    ("odi_pp", "new-ball bowler", {"over_min": 0, "over_max": 9}, {"odiwc": 250}, 3),
    ("death", "death bowler", {"over_min": 15, "over_max": 19}, {"ipl23": 180, "t20i23": 120}, 4),
    ("odi_death", "death bowler", {"over_min": 40, "over_max": 49}, {"odiwc": 120}, 3),
    ("middle", "middle-overs bowler", {"over_min": 6, "over_max": 14}, {"ipl23": 300, "t20i23": 200}, 2),
    ("spinner", "spinner", {"bowl_kind": ["spin bowler"]}, {"ipl23": 400, "t20i23": 300, "odiwc": 600}, 3),
    ("quick", "fast bowler", {"bowl_kind": ["pace bowler"]}, {"ipl23": 400, "t20i23": 300, "odiwc": 600}, 3),
]
PAIR_SCOPES = [
    ("odi_pair", "ODI partnerships since the 2023 World Cup (top 10)", "ODIs", "ODI",
     {"include_international": True, "top_teams": 10, "start_date": ODI_SINCE}, 400, 4),
    ("ipl_pair", "IPL partnerships since 2022", "IPL", "T20", {"leagues": ["IPL"], "start_date": "2022-01-01"}, 300, 3),
]


def candidates() -> List[Question]:
    out: List[Question] = []
    for scopes in (T20_SCOPES, ODI_SCOPES):
        for skey, hook, slabel, kicker, fmt, sparams in scopes:
            for role, situations in (("batter", BATTER_SITUATIONS), ("bowler", BOWLER_SITUATIONS)):
                for key, noun, filters, mins, prio in situations:
                    if skey not in mins:
                        continue
                    text = f"Who is the best {noun} {hook}?"
                    if role == "batter" and key == "all":
                        text = f"Who is the most complete batter {hook}?"
                    out.append(Question(
                        key=f"{skey}-{role}-{key}", text=text, role=role, fmt=fmt, params={**sparams, **filters},
                        min_balls=mins[skey], scope_label=f"{slabel} · {mins[skey]:,}+ balls", kicker=kicker,
                        priority=prio + (1 if skey == "ipl23" else 0), noun=noun))
    for key, label, kicker, fmt, params, mb, prio in PAIR_SCOPES:
        out.append(Question(key=key, text=f"What is the most complete {kicker if kicker != 'ODIs' else 'ODI'} partnership?",
                            role="partnership", fmt=fmt, params=params, min_balls=mb,
                            scope_label=f"{label} · {mb:,}+ balls together", kicker=kicker, priority=prio, noun="partnership"))
    return out


def contested(ctx: QuestionContext, chosen: List[A.Angle]) -> Dict[str, Any]:
    """Who leads each chosen angle; contested when they aren't all the same."""
    leaders = {a.id: (ctx.leader(a) or {}).get("name") for a in chosen}
    distinct = {v for v in leaders.values() if v}
    return {"leaders": leaders, "distinct": len(distinct), "contested": len(distinct) >= MIN_LEADERS}


def appeal(questions: List[Question]) -> Dict[str, float]:
    """Jev's 0..4 'would fans argue about this' per question key; {} without Jev."""
    if not questions or not jev_client.enabled():
        return {}
    answers = jev_client.ask(
        {"audience": "Indian and global cricket fans on Instagram", "questions": {q.key: q.text for q in questions}},
        {q.key: {"type": "score", "instructions": f"How much would cricket fans on Instagram argue about: \"{q.text}\"?",
                 "criteria": APPEAL_CRITERIA} for q in questions},
        timeout=10.0,
    ) or {}
    return {q.key: float((answers.get(q.key) or {}).get("score")) for q in questions
            if isinstance((answers.get(q.key) or {}).get("score"), (int, float))}


def generate(db, limit: int = 30, only: Optional[List[str]] = None, log=print) -> List[Dict[str, Any]]:
    """Every candidate that has a field, a plan and a contested answer, best first.

    Returns [{question, ctx, plan, contest, appeal}] — the post builder takes it from there.
    """
    kept = []
    for q in candidates():
        if only and q.key not in only:
            continue
        ctx = QuestionContext(db=db, role=q.role, fmt=q.fmt, params=q.params, min_balls=q.min_balls)
        try:
            n = ctx.n
        except Exception as exc:  # a bad filter combination: skip the question, keep going
            log(f"  skip {q.key}: query failed ({exc})")
            db.rollback()
            continue
        if n < 10:
            log(f"  skip {q.key}: only {n} in the field")
            continue
        p = plan(ctx, q.text, A.available(q.role, q.fmt, q.params.get("leagues") or ()))
        if len(p["angles"]) < 4:
            log(f"  skip {q.key}: only {len(p['angles'])} angles")
            continue
        c = contested(ctx, p["angles"])
        if not c["contested"]:
            log(f"  skip {q.key}: one leader on everything ({next(iter(c['leaders'].values()))})")
            continue
        kept.append({"question": q, "ctx": ctx, "plan": p, "contest": c})
    scores = appeal([k["question"] for k in kept])
    for k in kept:
        k["appeal"] = scores.get(k["question"].key, float(k["question"].priority))
        k["appeal_by"] = "jev" if k["question"].key in scores else "priority"
    kept.sort(key=lambda k: (-k["appeal"], -k["contest"]["distinct"], -k["question"].priority))
    return kept[:limit]

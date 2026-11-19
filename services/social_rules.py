"""
The social rules (docs/social_rules.md: Instagram posts, Reels, X) for code: its sections as text for LLM prompts and
Jev, and the rules code can test, as checks on a post's slides and a Reel's script. The Reddit title rules are
services/content_rules.py.

    section("Reels")            -> the section's bullets, for a prompt
    findings(slides, kind)      -> [{rule, slide, visual, message}]: each broken rule, by its RULES id
    lint_slides(slides)         -> ["Slide n: what's wrong", ...] for a queued post (shown in the admin as warnings)
    hook_problem(hook)          -> why a Reel hook breaks the rules, or None (the Reel writer's guard rejects it)
    caption_problems(caption)   -> what an Instagram caption breaks (length, tags, its first line), as warnings
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

RULES_FILE = Path(__file__).resolve().parents[1] / "docs" / "social_rules.md"
MAX_TITLE = 80  # two lines on a 4:5 card (docs/social_rules.md, Card anatomy)
MAX_SLIDES = 8
#: Metric names that lose a stranger in the first seconds of a Reel.
#: Words the house vocabulary replaces (docs/social_rules.md, Vocabulary): the term to use instead.
OFF_VOCAB = {"runs added": "Impact", "win chances": "win probability added", "new ball": "a phase name (powerplay)",
             "new-ball": "a phase name (powerplay)", "balls per dismissal": "balls per wicket", "out every": "balls per wicket",
             "runs above an average": "runs above par", "runs saved vs an average": "runs below par"}
OFF_VOCAB_RE = re.compile("|".join(re.escape(k) for k in OFF_VOCAB), re.I)

#: Cards that are words, not a picture: a carousel slide is a claim and a chart (docs/social_rules.md, Card anatomy).
TEXT_VISUALS = {"recap_text"}
#: A count of one with a plural noun ("1 overs"): name the one instead ("the 19th over").
ONE_PLURAL = re.compile(r"(?<![\d.])\b(?:1|one) (overs|balls|runs|wickets|sixes|fours|matches|innings|games|spells|points)\b", re.I)

JARGON = re.compile(r"\b(impact|wpa|raa|waa|win probability|runs above average|runs above par|against par|"
                    r"wins added|per 100|per hundred)\b", re.I)

#: Instagram's limits and the fold (SOCIAL_COPY_PLAN.md S3).
CAPTION_MAX = 2200     # Instagram refuses a longer caption
CAPTION_TAGS = 5       # Instagram's hashtag limit
CAPTION_FOLD = 125     # characters shown before "more"


@lru_cache(maxsize=1)
def _sections() -> Dict[str, str]:
    try:
        text = RULES_FILE.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - the rules are guidance; a missing file never stops a post
        return {}
    out: Dict[str, str] = {}
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        out[head.strip()] = body.strip()
    return out


def section(name: str) -> str:
    """A section's bullets as written ('' when it's missing)."""
    return _sections().get(name, "")


def _list_too_long(sentence: str) -> bool:
    """More than three items: four or more comma-separated parts, the last joined by "and"/"or" ("A, B, C and D").
    Commas in brackets and in numbers ("2,000") don't count, nor clauses that aren't a list."""
    flat = re.sub(r"(?<=\d),(?=\d)", "", re.sub(r"\([^)]*\)", "", sentence))
    parts = [p for p in flat.split(", ") if p.strip()]
    return len(parts) >= 4 and bool(re.search(r"\b(and|or)\b", parts[-1]))


#: Every rule the lint checks, by id: what the audit (scripts/audit_social_rules.py) and the gate group findings by.
RULES = {
    "text_card": "a text card in the deck",
    "one_plural": "a count of one with a plural noun",
    "long_title": f"a title over {MAX_TITLE} characters",
    "title_list": "a list of more than three in a title",
    "long_help": "a long help line drawn on the card",
    "vocabulary": "a word the house vocabulary replaces",
    "lonely_ring": "a 'best' ring where only one row has a value",
    "bare_cover": "no chart on the cover, and none in the deck that can be one",
    "slide_count": f"more than {MAX_SLIDES} slides",
    "cover_repeat": "the cover's chart repeated in the deck",
    "deeper_cut_slot": "the deeper cut not on its slide",
}
#: Kinds of post that are a reference deck (one slide per team, a round-up): saved and sent, so past 8 slides is fine.
REFERENCE_KINDS = {"reference"}


#: What only the drawn slide shows, measured at render (scripts/lib/slide_layout.mjs, stored as facts.layout).
LAYOUT_RULES = {
    "title_lines": "a title over 2 lines, as drawn",
    "title_clipped": "a title cut off, as drawn",
    "footer_lines": "a scope line that wraps",
    "legend": "a legend chip that's a sentence",
    "text_clipped": "a label cut short with an ellipsis",
    "label_outside": "a chart label cut off at the edge",
    "label_overlap": "two chart labels on each other",
    "card_overflow": "a chart that doesn't fit its card",
    "small_chart": "a chart under 35% of the card",
}


def card_findings(card: Dict[str, Any]) -> List[Dict[str, str]]:
    """[{rule, message}] for one card (rule: a RULES id)."""
    out: List[Dict[str, str]] = []
    add = lambda rule, message: out.append({"rule": rule, "message": message})  # noqa: E731
    title = card.get("title") or ""
    if card.get("visual") in TEXT_VISUALS:
        add("text_card", "A text card: a slide is a claim and a picture; put the words in the caption")
    m = ONE_PLURAL.search(title)
    if m:
        add("one_plural", f"{m.group(0)!r} in the title: name the one instead")
    if len(title) > MAX_TITLE:
        add("long_title", f"Title over {MAX_TITLE} characters ({len(title)}): it won't fit the slide")
    for sentence in re.split(r"(?<=[.!?])\s+", title):
        if _list_too_long(sentence):
            add("title_list", "A list of more than three in the title")
            break
    # A help line is only drawn on the card with help_on_card (else it's in the info sheet): only a drawn one counts.
    if card.get("help") and card.get("help_on_card") and len(card["help"]) > 90:
        add("long_help", "A long help line drawn on the card: shorten it, or move it to the info sheet")
    seen = set()
    for where in (title, card.get("help") or "", card.get("sample") or "", str((card.get("payload") or {}).get("metric") or "")):
        for m in OFF_VOCAB_RE.finditer(where):
            k = m.group(0).lower()
            if k == "runs added" and re.search(r"\bimpact\b", where, re.I):
                continue  # "Impact: runs added to the projected total" defines Impact, it doesn't replace it
            if k not in seen:
                seen.add(k)
                add("vocabulary", f"Say {OFF_VOCAB[k]!r}, not {m.group(0)!r} (docs/social_rules.md, Vocabulary)")
    payload = card.get("payload") or {}
    if card.get("visual") == "scorecard" and payload.get("rows"):
        rows = payload["rows"]
        for m in payload.get("metrics") or []:
            k = m.get("key")
            have = [r for r in rows if (r.get("values") or {}).get(k) is not None]
            if len(have) == 1 and k in (have[0].get("leader") or []):
                add("lonely_ring", f"A 'best' ring on {k!r}, where only one row has a value")
    return out


def lint_card(card: Dict[str, Any]) -> List[str]:
    return [f["message"] for f in card_findings(card)]


def findings(slides: List[Dict[str, Any]], kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every testable carousel rule broken by a post's slides: [{rule, slide (None for the deck), visual, message}].
    kind: the post's kind (a play-along keeps its deeper cut after the answer, on purpose)."""
    out: List[Dict[str, Any]] = []
    hero = ((slides[0].get("hero") or {}).get("card") if slides and isinstance(slides[0], dict) else None) or {}
    if slides and slides[0].get("type") == "hook" and slides[0].get("cover") == "text-no-chart":
        out.append({"rule": "bare_cover", "slide": 1, "visual": None,
                    "message": "no chart on the cover, and no card in the deck that can be one: lead with a chart "
                               "(services/ig_cover.hero_from lists the ones that fit)"})
    if len(slides or []) > MAX_SLIDES and kind not in REFERENCE_KINDS:
        out.append({"rule": "slide_count", "slide": None, "visual": None,
                    "message": f"{len(slides)} slides: keep a carousel to {MAX_SLIDES} (completion counts)"})
    for n, s in enumerate(slides or [], 1):
        c = s.get("card") if isinstance(s, dict) else None
        if not c:
            continue
        out += [{**f, "slide": n, "visual": c.get("visual")} for f in card_findings(c)]
        if hero and n > 1 and (c.get("id") == hero.get("id") or c.get("title") == hero.get("title")):
            out.append({"rule": "cover_repeat", "slide": n, "visual": c.get("visual"),
                        "message": "repeats the cover's chart; the cover already shows it, so drop it from the deck"})
        want = 2 if (slides[0].get("hero") if slides else None) else 3  # a hero cover takes the lead card off the deck
        if (c.get("kicker") or "").lower() == "the deeper cut" and n not in (want, 3) and kind != "play":
            out.append({"rule": "deeper_cut_slot", "slide": n, "visual": c.get("visual"),
                        "message": f"the deeper cut belongs on slide {want}"})
    return out


def lint_slides(slides: List[Dict[str, Any]], kind: Optional[str] = None) -> List[str]:
    """findings() as 'Slide n: ...' warnings, as the admin shows them."""
    return [f"Slide {f['slide']}: {f['message']}" if f["slide"] else f["message"] for f in findings(slides, kind)]


def thread_problems(tweets: List[Dict[str, Any]], players: Optional[List[str]] = None) -> List[str]:
    """X thread rules a thread breaks (docs/social_rules.md, X): one or two tags on tweet 1 and none after, at most four
    images a tweet, nothing over 280. `players` is kept for the callers (names are plain text now)."""
    from services.ig_x import LIMIT, MAX_IMAGES, MAX_TAGS, weight

    out = []
    tweets = list(tweets or [])
    if tweets and len(tweets[0].get("slides") or []) > 1:
        out.append(f"tweet 1: {len(tweets[0]['slides'])} images (one: tweet 1's image shows tall)")
    # group the slides, up to four a tweet: one tweet per slide is the carousel retyped (18 Nov scorecard thread)
    images = sum(len(t.get("slides") or []) for t in tweets)
    most = 2 + -(-max(0, images - 1) // MAX_IMAGES)  # tweet 1, the rest four at a time, one spare (text or link)
    if len(tweets) > most:
        out.append(f"{len(tweets)} tweets for {images} images: group the slides, up to {MAX_IMAGES} a tweet "
                   f"({most} tweets at most)")
    for t in tweets:
        text, n = t.get("text") or "", t.get("n")
        tags = re.findall(r"(?<![\w&])#\w+", text)
        if n == 1 and len(tags) > MAX_TAGS:
            out.append(f"tweet 1: {len(tags)} hashtags ({MAX_TAGS} at most)")
        if n != 1 and tags:
            out.append(f"tweet {n}: hashtags after tweet 1 ({' '.join(tags)})")
        if len(t.get("slides") or []) > MAX_IMAGES:
            out.append(f"tweet {n}: {len(t['slides'])} images ({MAX_IMAGES} at most)")
        if weight(text) > LIMIT:
            out.append(f"tweet {n}: {weight(text)} characters")
    return out


def youtube_problems(yt: Optional[Dict[str, Any]]) -> List[str]:
    """What a Short's copy breaks (docs/social_rules.md, Captions and YouTube): a title that's missing, over 60
    characters, cut with "…", or cut mid-thought (it doesn't end on a whole word run that says something: the hook
    shortened to "...4 of 7 roles at playoff", 18 Nov). Set the post's own `yt_title`, a search phrase."""
    from services.ig_notes import YT_TITLE

    if not yt:
        return []
    title = (yt.get("title") or "").strip()
    if not title:
        return ["The Short has no title: set the post's yt_title (a search phrase, 60 characters at most)"]
    out = []
    if len(title) > YT_TITLE:
        out.append(f"The Short's title is {len(title)} characters ({YT_TITLE} at most)")
    if title.endswith(("…", "...")):
        out.append("The Short's title is cut with an ellipsis: set the post's yt_title")
    return out


def caption_problems(caption: str) -> List[str]:
    """What an Instagram caption breaks (SOCIAL_COPY_PLAN.md S3): Instagram's length and hashtag limits, and a first
    line (all a stranger sees before "more") that doesn't lead with a number or runs past the fold."""
    c = (caption or "").strip()
    if not c:
        return []
    out = []
    if len(c) > CAPTION_MAX:
        out.append(f"Caption is {len(c)} characters: Instagram stops at {CAPTION_MAX}")
    tags = re.findall(r"(?<![\w&])#\w+", c)
    if len(tags) > CAPTION_TAGS:
        out.append(f"{len(tags)} hashtags: Instagram takes {CAPTION_TAGS}")
    first = c.splitlines()[0].strip()
    if re.match(r"news first\b", first, re.I):
        out.append("Caption opens on the news: lead with the player and the number, the news after")
    elif not re.search(r"\d", first[:CAPTION_FOLD]):
        out.append(f"No number in the caption's first {CAPTION_FOLD} characters (all that shows before \"more\")")
    sentence = re.split(r"(?<=[.!?])\s", first, maxsplit=1)[0]
    if len(sentence) > CAPTION_FOLD:
        out.append(f"Caption's first sentence is {len(sentence)} characters: only {CAPTION_FOLD} show before \"more\", "
                   f"so the claim gets cut")
    return out


def hook_problem(hook: str) -> Optional[str]:
    """Why a Reel hook breaks the Reel rules (a number, no metric names), or None."""
    h = (hook or "").strip()
    if not re.search(r"\d", h):
        return "the hook has no number: open on one player and one plain number"
    m = JARGON.search(h)
    if m:
        return f"the hook uses a metric name ({m.group(0)!r}): say it in plain words, explain the metric later"
    return None


# --- Motion Reels (MOTION_REEL_PLAN.md M7): checks on a reel spec and on its recorded video. ---------------------------
#
# The frame and the numbers live in src/components/ig/reel/frame.json, read by the Reel page too, so the page and these
# checks can't drift apart.

REEL_FRAME_FILE = Path(__file__).resolve().parents[1] / "src" / "components" / "ig" / "reel" / "frame.json"
#: Kinds whose ring is on a decision with both sides shown at the same size (no single negative mark is singled out).
REEL_BOTH_SIDES = {"case_board", "pick_one", "keep_try"}
#: Average advance of a character, in em, for the faces the Reel fits to one line (motion.js EM_PER_CHAR).
REEL_EM = {"mono": 0.6 + 0.14, "display": 0.5}


@lru_cache(maxsize=1)
def reel_frame() -> Dict[str, Any]:
    import json
    return json.loads(REEL_FRAME_FILE.read_text())


def reel_captions(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The caption lines a spec shows: its `captions`, or built from its voice `timing` exactly as the Reel page does
    (motion.js captionsFromTiming): break at sentence ends and colons, at commas after two words, at five words and
    before a word that would pass 30 characters;
    a one-word orphan joins the line before, or takes a word from a full one."""
    if spec.get("captions"):
        return spec["captions"]
    timing = spec.get("timing")
    if not timing:
        return []
    caps: List[List[Dict[str, Any]]] = []
    for li, line in enumerate(timing["lines"]):
        cur: List[Dict[str, Any]] = []
        ws = line.split(" ")
        for wi, w in enumerate(ws):
            if cur and len(" ".join([x["w"] for x in cur] + [w])) > reel_frame()["rules"]["captionChars"]:
                caps.append(cur)  # one line: a word that would pass the limit starts the next
                cur = []
            cur.append({"w": w, "at": timing["words"][li][wi], "li": li})
            brk = re.search(r"[.?!:]$", w) or (w.endswith(",") and len(cur) >= 2) or len(cur) >= 5
            if brk or wi == len(ws) - 1:
                caps.append(cur)
                cur = []
    for i in range(len(caps) - 1, 0, -1):
        if len(caps[i]) == 1 and caps[i][0]["li"] == caps[i - 1][0]["li"]:
            if len(caps[i - 1]) < 5 and len(" ".join(x["w"] for x in caps[i - 1] + caps[i])) <= reel_frame()["rules"]["captionChars"]:
                caps[i - 1].extend(caps[i])
                del caps[i]
            else:
                caps[i].insert(0, caps[i - 1].pop())
    return [{"start": c[0]["at"], "words": [{"w": x["w"], "at": x["at"]} for x in c]} for c in caps]


def _overlaps(a: Dict[str, float], b: Dict[str, float]) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def _fit_px(text: str, width: float, most: float, face: str) -> float:
    return min(most, width / (max(1, len(text or "")) * REEL_EM[face]))


def _item_value(payload: Any, key: str) -> Optional[float]:
    """The number a ring's key points at in a scene's payload or data: a row, chip or player named `key` (name, label,
    short or key), or a grid cell "<row> · <column>". None when the key names nothing with a number."""
    if not isinstance(payload, dict):
        return None
    if " · " in key and payload.get("cols") and payload.get("rows"):
        row, col = key.rsplit(" · ", 1)
        if col in payload["cols"]:
            j = payload["cols"].index(col)
            for r in payload["rows"]:
                if r.get("name") == row and j < len(r.get("cells") or []):
                    cell = r["cells"][j]
                    return cell.get("value") if isinstance(cell, dict) else None
    found: List[float] = []

    def walk(o: Any) -> None:
        if isinstance(o, dict):
            names = {o.get(k) for k in ("name", "label", "short", "key", "n")}
            if key in names:
                for k in ("value", "v", "subject"):
                    if isinstance(o.get(k), (int, float)):
                        found.append(o[k])
                        return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(payload)
    return found[0] if found else None


def reel_problems(spec: Dict[str, Any]) -> List[str]:
    """What a motion Reel's spec breaks (docs/social_rules.md, Reels; MOTION_REEL_PLAN.md M7): length, scene order and
    minimum time on screen, how long a lit item holds before the next, caption size, the closing scene's captions,
    kicker and send-line sizes, the frame against Instagram's overlays, and a ring on a below-par mark (no-blame: a
    negative number is never singled out, except inside a decision that shows both sides). The longest still stretch
    needs the recorded video: reel_still_problems()."""
    F = reel_frame()
    R = F["rules"]
    out: List[str] = []
    scenes = spec.get("scenes") or []
    if not scenes:
        return ["The Reel has no scenes"]
    d = spec.get("duration") or 0
    if not (R["lengthMin"] <= d <= R["lengthMax"]):
        out.append(f"The Reel runs {d:.1f}s: keep it {R['lengthMin']}-{R['lengthMax']}s")
    if scenes[0].get("start") != 0:
        out.append("The first scene must start at 0 (frame 0 is never empty)")
    for i, s in enumerate(scenes):
        a, b = s.get("start", 0), s.get("end", 0)
        name = f"Scene {i + 1} ({s.get('kind')})"
        if i and a < scenes[i - 1].get("start", 0):
            out.append(f"{name} starts before the scene before it")
        if b - a < R["sceneMin"]:
            out.append(f"{name} is on screen {b - a:.1f}s: a must-read number needs {R['sceneMin']}s")
        elif s.get("kind") not in ("hero", "pick_one") and R.get("drawn"):
            # a chart must finish drawing and then stay up long enough to read (charts cut off mid-draw, 18 Nov)
            draw = R["drawn"].get(s.get("kind"), R["drawn"]["default"])
            if b - a < draw + R["drawn"]["hold"]:
                out.append(f"{name} is on screen {b - a:.1f}s: its chart draws for {draw}s and must then hold "
                           f"{R['drawn']['hold']}s (give it {draw + R['drawn']['hold']:.1f}s, or fewer scenes)")
        beats = sorted((x for x in (s.get("beats") or []) if x.get("key") is not None), key=lambda x: x["at"])
        for x, y in zip(beats, beats[1:]):
            if y["at"] - x["at"] < R["dwellMin"] - 1e-3:
                out.append(f"{name}: {x['key']} is lit {y['at'] - x['at']:.2f}s before {y['key']}: hold each {R['dwellMin']}s")
        if s.get("kind") not in REEL_BOTH_SIDES:
            body = s.get("payload") or s.get("data")
            for x in beats:
                v = _item_value(body, x["key"])
                if v is not None and v < 0:
                    out.append(f"{name}: the ring lands on {x['key']} ({v:+g}), a below-par mark: no-blame, ring the case "
                               f"for or a regular's number instead")
        if s.get("kicker") and _fit_px(s["kicker"], F["kicker"]["w"], 30, "mono") < R["kickerMinPx"]:
            out.append(f"{name}: the kicker is too long for one line ({len(s['kicker'])} characters)")
        send = ((s.get("data") or {}).get("send") or {}).get("text")
        if send and _fit_px(send, F["content"]["w"], 66, "display") < R["sendMinPx"]:
            out.append(f"{name}: the send line is too long for one line ({len(send)} characters)")
    if scenes[-1].get("captions") is not False:
        out.append("The closing scene must turn captions off (the send line is the caption)")
    for i, c in enumerate(reel_captions(spec)):
        words = [w["w"] for w in c.get("words") or []]
        if len(words) > R["captionWords"]:
            out.append(f"Caption {i + 1} has {len(words)} words: at most {R['captionWords']}")
        if len(" ".join(words)) > R["captionChars"]:
            out.append(f"Caption {i + 1} is {len(' '.join(words))} characters: at most {R['captionChars']} (one line)")
    for box in ("chapters", "kicker", "content", "caption"):
        for k in F["keepClear"]:
            if _overlaps(F[box], k):
                out.append(f"The frame's {box} sits in Instagram's {k['name']}")
    return out


def reel_still_problems(video: str, limit: Optional[float] = None) -> List[str]:
    """The longest still stretch in a recorded Reel's content zone (docs/social_rules.md: something moves at least every
    0.8s; the closing scene's breathing tiles count as moving). ffmpeg's freezedetect on the content zone, cropped from
    the frame (frame.json), at -55dB: calibrated on the round-2 Reel, where it finds the ranked bars holding still
    between beats and passes the hero card's slow bob; the glow behind is under that floor. Record the video with the
    visuals' bob off (scripts/record_ig_reel.mjs --nodrift): the bob alone would always pass."""
    import subprocess
    F = reel_frame()
    lim = limit if limit is not None else F["rules"]["stillMax"]
    c = F["content"]
    run = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-vf",
                          f"crop={c['w']}:{c['h']}:{c['x']}:{c['y']},freezedetect=n=-55dB:d={lim}", "-an", "-f", "null", "-"],
                         capture_output=True, text=True)
    out = []
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", run.stderr)]
    durs = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", run.stderr)]
    for a, dur in zip(starts, durs):
        out.append(f"Nothing moves from {a:.1f}s for {dur:.1f}s: something must change every {lim}s")
    if len(starts) > len(durs):  # still to the end of the video
        out.append(f"Nothing moves from {starts[-1]:.1f}s to the end: something must change every {lim}s")
    return out

"""
Reel v2: a 15-20 second Reel that opens on the post's payoff chart, voiced and captioned, instead of the carousel played
as a silent slideshow (services/ig_slides.make_reel, v1).

    make(carousel_id, slides, voice=None, base=SITE, store=True, out=None)  ->  {seconds, script, source, voice, mp4}
    for_carousel(carousel_id)  ->  seconds, or None (not eligible / the A/B day is v1 / it failed: v1 is made instead)

1. beats: the 2-3 strongest cards: the payoff (a win-probability line, a record race, a bowling plan, a highlighted
   bar chart ...), the deeper cut, one more. Previews and play-alongs get no v2 Reel.
2. script: GPT-4o-mini writes a hook and one line per beat from the cards' titles and help lines; the guard rejects it if
   any number isn't on the cards, or it's too long (one retry, then a template from the titles). Stored with its source.
3. voice: OpenAI TTS, one clip per line, so each beat lasts exactly as long as its line.
4. frames: scripts/record_ig_beats.mjs records each beat's chart revealed left to right (/ig/<id>/<n>?animate=1).
5. compose (ffmpeg): 1080x1920; the slide in the middle (as v1); the hook in big type above it while it's spoken, then
   the brand; captions below, a few words at a time in step with the voice; a quiet generated music bed under the voice.

The voice is AI-generated, so the caption says so (services/ig_captions.with_ai_voice) and admin reminds the user to
turn on Instagram's AI label. No number reaches the voice that isn't on the slides.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
FONT_BOLD = ROOT / "api/_lib/fonts/BarlowSemiCondensed-Bold.ttf"
FONT_BODY = ROOT / "api/_lib/fonts/Barlow-SemiBold.ttf"
SITE = os.getenv("REEL_BASE", "https://hindsightcricket.com")
VOICE = os.getenv("REEL_VOICE", "verse")
TTS_MODEL = "gpt-4o-mini-tts"
SCRIPT_MODEL = os.getenv("REEL_SCRIPT_MODEL", "gpt-4o")   # follows the fairness rules far better than 4o-mini
#: How the voice speaks (gpt-4o-mini-tts instructions): REEL_TONE overrides it, like REEL_VOICE, without a deploy.
TONE = os.getenv("REEL_TONE") or ("Brisk, confident cricket analyst on a highlights show: a quick, lively pace. "
                                  "Conversational, energetic but not shouty; land each number clearly; slight lift on the hook.")
FPS = 30
W, H, SLIDE_H, TOP = 1080, 1920, 1350, 285
BG = "0x0a0c11"
GAP = 0.12                     # seconds of silence between lines
#: Two lengths: short (about 25-30s, 3 charts) and long (45-60s, up to 5 charts, room for the advanced metrics).
LENGTHS = {
    "short": {"words": (45, 76), "say": "55 to 72", "spoken": "about 28 seconds", "seconds": 30, "beats": 3},
    "long": {"words": (75, 175), "say": "90 to 160", "spoken": "35 to 60 seconds", "seconds": 60, "beats": 5},
}
WORDS = LENGTHS["short"]["words"]
MAX_SECONDS = 60
TEMPO = float(os.getenv("REEL_TEMPO", "1.12"))   # the voice sped up, pitch kept (ffmpeg atempo)
# Seconds of the carousel's first slide, still, before the story: 0 by default, since a still opening lost two in three
# viewers in the first 3s (12 Oct). The cover is picked when posting instead (admin: Reel tab → Cover).
COVER_SECONDS = float(os.getenv("REEL_COVER", "0"))
CAPTION_WORDS = 3              # words on screen at a time
ELIGIBLE = ("recap", "spotlight", "record", "trend", "debate", "weird", "myth", "preview")
#: A match preview's Reel, in story order: what wins here, who's in form, who suits the ground, who has gone big here,
#: the match-up, and a milestone to close on. The first k the carousel has; the milestone is kept as the closer.
PREVIEW_BEATS = ("totals", "form-strips", "suits-ground", "ground-records", "key-battles", "milestones")
#: The payoff, in order of preference: what opens the Reel.
PAYOFF = ("win_prob_line", "race_lines", "bowling_plan", "metric_bars", "deep_compare", "scorecard", "bucket_bars",
          "boundary_zones", "pair_dumbbell", "scatter_plus")
SKIP = ("innings_scorecard", "xis", "innings_wagon")   # walls of text: not a Reel beat


# ---- beats ----------------------------------------------------------------------------------------------------------

def beats(slides: List[Dict[str, Any]], k: int = 3) -> List[Tuple[int, Dict[str, Any]]]:
    """[(slide number, card)]: the payoff first, then the deeper cut, then the next card; at most k."""
    cards = [(i + 1, s["card"]) for i, s in enumerate(slides) if s.get("type") == "card" and s.get("card")
             and s["card"].get("visual") not in SKIP]
    if not cards:
        return []
    picks = preview_beats(cards, k)
    if picks:
        return picks

    def rank(c):
        v = c[1].get("visual")
        highlighted = any(r.get("highlight") for r in (c[1].get("payload") or {}).get("rows") or [] if isinstance(r, dict))
        base = PAYOFF.index(v) if v in PAYOFF else len(PAYOFF)
        return (base - (0.5 if highlighted and v == "metric_bars" else 0), c[0])
    payoff = min(cards, key=rank)
    out = [payoff]
    deep = next((c for c in cards if c[1].get("kicker") and c is not payoff), None)
    if deep:
        out.append(deep)
    for c in cards:
        if len(out) >= k:
            break
        if c not in out:
            out.append(c)
    return [out[0]] + sorted(out[1:], key=lambda c: c[0])


def preview_beats(cards: List[Tuple[int, Dict[str, Any]]], k: int) -> List[Tuple[int, Dict[str, Any]]]:
    """A preview's beats (PREVIEW_BEATS order), or [] when the carousel has fewer than two of them. Over k, cards are
    dropped from the end, except a closing milestone."""
    by_id = {c.get("id"): (n, c) for n, c in cards}
    picks = [by_id[i] for i in PREVIEW_BEATS if i in by_id]
    if len(picks) < 2:
        return []
    while len(picks) > k:
        picks.pop(-2 if picks[-1][1].get("id") == "milestones" else -1)
    return picks


def by_card_id(slides: List[Dict[str, Any]], ids: List[str]) -> List[int]:
    """Slide numbers for card ids (scripts/make_reel_v2.py --cards), in the order given; unknown ids are an error."""
    where = {s["card"].get("id"): i + 1 for i, s in enumerate(slides) if s.get("type") == "card" and s.get("card")}
    missing = [i for i in ids if i not in where]
    if missing:
        raise ValueError(f"not in this carousel: {', '.join(missing)}")
    return [where[i] for i in ids]


# ---- the script -----------------------------------------------------------------------------------------------------

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(text: str) -> set:
    """The numbers in a text, as strings without thousands commas ("1,024" -> "1024", "0.27" -> "0.27")."""
    return {n.replace(",", "").rstrip(".") for n in _NUM.findall(text or "")}


def _short(n: str) -> str:
    """"11.10" -> "11.1", "8.0" -> "8"; whole numbers are left alone ("30" stays "30")."""
    return n.rstrip("0").rstrip(".") if "." in n else n


def _flatten(v) -> List[str]:
    if isinstance(v, dict):
        return [x for i in v.values() for x in _flatten(i)]
    if isinstance(v, (list, tuple)):
        return [x for i in v for x in _flatten(i)]
    if isinstance(v, bool) or v is None:
        return []
    if isinstance(v, (int, float)):
        # Exact values only (as charts show them): 28.9 never allows "29" or "30".
        f = abs(float(v))
        if f.is_integer():
            return [str(int(f))]
        return [_short(f"{f:.1f}"), _short(f"{f:.2f}")]
    return [str(v)]


def allowed(hook: str, bs: List[Tuple[int, Dict[str, Any]]]) -> set:
    """Every number the script may say: those in the hook, the beats' titles and help lines, and their chart values."""
    text_ = " ".join([hook] + [f"{c.get('title', '')} {c.get('help', '')}" for _, c in bs])
    nums = numbers(text_)
    for _, c in bs:
        nums |= numbers(" ".join(_flatten(c.get("payload"))))
    return nums | {_short(n) for n in nums}


def guard(script: Dict[str, Any], ok: set, k: int, words_range: Tuple[int, int] = WORDS) -> Optional[str]:
    """None if the script is usable, else why not."""
    lines = script.get("lines")
    if not isinstance(script.get("hook"), str) or not isinstance(lines, list) or len(lines) != k:
        return "shape"
    words = len(" ".join([script["hook"], *lines]).split())
    if not words_range[0] <= words <= words_range[1]:
        return f"{words} words"
    h = script["hook"].strip()
    stats = lambda t: {m.rstrip("%").replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?%?", t)
                       if "%" in m or "." in m}  # noqa: E731  percentages and decimals: the stats people notice twice
    again = stats(h) & stats(lines[0])
    if again:
        return f"the first line repeats the hook's {', '.join(sorted(again))}: move the story on instead"
    if h.endswith("?") and not numbers(h) and len(re.split(r"(?<=[.!?])\s+", h)) < 2:
        return "the hook is a bare question: give it a number or a sharp claim first (\"X happened. But why?\")"
    said = numbers(" ".join([script["hook"], *lines]))
    extra = {n for n in said if n not in ok and _short(n) not in ok}
    return f"numbers not on the cards: {sorted(extra)}" if extra else None


def _trim(text: str, words: int) -> str:
    """A title cut to about `words` words, at a clause boundary where one is close."""
    parts = re.split(r"(?<=[.;:])\s+|,\s+(?=[a-z])", text.strip())
    out = ""
    for p in parts:
        if out and len((out + " " + p).split()) > words:
            break
        out = (out + " " + p).strip()
    return " ".join(out.split()[:words + 4]).rstrip(",;:") + ("" if out.endswith((".", "?", "!")) else ".")


def template(hook: str, bs: List[Tuple[int, Dict[str, Any]]]) -> Dict[str, Any]:
    return {"hook": _trim(hook, 14), "lines": [_trim(c.get("title", ""), 16) for _, c in bs]}


def _client():
    from openai import OpenAI

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=key)


PROMPT = """You write the voiceover for a %(spoken)s Instagram Reel about cricket data.
Return JSON: {"hook": string, "lines": [string, ...]} with exactly %(k)d lines, one per chart, in the order given.
It is ONE story told in %(spoken)s, spoken in one take: the hook sets it up, the lines carry it forward, the last
line lands it. The video cuts to each chart as its line starts, so each line is the moment the story reaches that chart.
Rules:
- Make it flow like a person telling a story: each line follows from the one before ("But...", "Here's the thing...",
  "So...", "And yet..."). Never read a chart's title out; the chart shows the number, you say why it matters.
- HARD LIMIT: %(say)s words in total, hook included (%(spoken)s spoken, briskly). Use only as many as the story
  needs: never pad. Count them before you answer.
  Spoken English, short sentences.
- Don't repeat the hook in the first line: the first line moves the story on.
- The hook comes first and must grab in the first 2 seconds, in under 12 words, keeping the key name. It can be a
  statement or a question, but never a bare generic question: a question needs a number or a sharp claim with it
  ("A big first over dents Varun's numbers. Is it just him?"). Don't just repeat the post hook. The hook must agree with THE VERDICT when there is one, and
  with what the charts show; never claim more than they do. Use a number in the hook when one carries the answer.
- Be specific, never hype: no "like no one else", "elite", "insane", "massive", "game-changer", "shines", "knack",
  "unmatched", "plummets", "crashes", "collapses", "sharply", "skyrockets". Let the two numbers show the size; say
  win probability numbers as "percentage points". A precise claim beats a big one.
  When the verdict is inconclusive or partly, the hook states what the charts DO show and the doubt, as a statement,
  e.g. "A bad first over hurts Varun. It hurts every spinner." or "The data doesn't back the Varun myth."
- Write a negative number with the word "minus" (e.g. "minus 0.29"), never a minus sign.
- Each line is one to three short sentences about its chart. When a line uses an advanced metric (runs saved or added
  against an average player, win probability added, Impact), explain it inside that same sentence, the first time,
  e.g. "he saves 0.8 runs an over compared with an average bowler in the same spot" -- never as a separate definition.%(extra)s
- Use ONLY numbers that appear in the material below, written as digits exactly as given (e.g. 85%%, 1,024, 0.27).
  Never round, combine, or compute new numbers, and never compute comparisons in words ("twice", "double", "half",
  "three times"): give both numbers instead. If unsure, leave the number out.
- Line N is spoken while chart N is on screen: it must be about THAT chart's numbers, in the order given.
- State only facts that a chart's title or help line says, in your own words. Don't draw new conclusions from the
  numbers (a level is not a difference: "0.59 with him" is not "0.59 more").
- Be fair: don't blame players; describe what happened. Don't overclaim: a small lead is "slightly", a mixed result is
  "mixed". If the material has a doubt or a cost, say it.
- Keep every claim's scope, in the hook too: a number "against top sides" must say so; "among India's pacers" never
  becomes "no one"; "at the death" stays at the death; "1 of 5
  tests finds a clear effect" means the evidence is mixed, so no "crash", "big dip" or flat yes/no. "Only", "the best",
  "none have matched" need a chart's rows to prove them; a lead of a couple of balls is "slightly", not "no one matches".
- Never list more than three things in one sentence. No hashtags, no emojis, no "in this video".
- End the last line with a short question that invites a comment, or a punchy closer.

Post hook: %(hook)s

Charts:
%(charts)s
%(notes)s"""


def script_llm(hook: str, bs: List[Tuple[int, Dict[str, Any]]], feedback: str = "", notes: str = "",
               length: str = "short", close: str = "") -> Dict[str, Any]:
    charts = "\n".join(f"{i + 1}. {c.get('title', '')}" + (f" ({c['help']})" if c.get("help") else "")
                       for i, (_, c) in enumerate(bs))
    L = LENGTHS[length]
    extra = ("\n- Around the middle, turn the story with a re-hook (e.g. \"But here's what the scorecard doesn't show.\")"
             " so people who drift come back. Give the advanced numbers room: that is why this Reel is longer."
             if length == "long" else "")
    msg = PROMPT % {"k": len(bs), "hook": hook, "charts": charts, "say": L["say"], "spoken": L["spoken"], "extra": extra,
                    "notes": f"\nAlso on the slides (may be used in the lines, e.g. the doubts):\n{notes}\n" if notes else ""}
    if close:
        msg += f"\nEnd the last line with exactly this question: \"{close}\""
    if feedback:
        msg += (f"\nYour last attempt was rejected ({feedback}). Fix that"
                + (f": land within {L['say']} words." if "words" in feedback else f", and keep it {L['say']} words long.")
                + " Keep everything else that worked.")
    resp = _client().chat.completions.create(model=SCRIPT_MODEL, temperature=0.6,
                                             response_format={"type": "json_object"},
                                             messages=[{"role": "user", "content": msg}])
    return json.loads(resp.choices[0].message.content or "{}")


def notes_of(slides: List[Dict[str, Any]]) -> str:
    """The post's own text slides (the claim, the doubts) as extra material for the script. Credited outside figures
    ("From elsewhere", "Source: ...") are left out: they're shown on a slide with their source, never voiced."""
    out = []
    for s in slides:
        if s.get("type") == "verdict":  # a myth test's answer: the hook must agree with it
            out.append(f"THE VERDICT (the post's answer): {s.get('verdict')}: "
                       f"{' / '.join(l for l in (s.get('body') or '').splitlines() if l.strip())}")
            continue
        if s.get("type") != "text":
            continue
        heading, body = s.get("heading") or "", s.get("body") or ""
        if "elsewhere" in heading.lower() or "source:" in body.lower():
            continue
        out.append(f"{heading}: {' / '.join(l for l in body.splitlines() if l.strip())}")
    return "\n".join(out)


CHECK = """You check a cricket Reel voiceover against its source material.
Reply JSON {"problems": [...]} listing ONLY real problems (an empty list if there are none). Never list a claim that is
fine. A problem is:
- a claim beyond the material's scope ("among India's pacers" turned into "no one"; "at the death" dropped), or
  "only", "the best", "none have matched" that the chart's rows don't prove;
- a line that isn't about its own chart (line 1 goes with chart 1, line 2 with chart 2, and so on);
- a comparison computed in words ("twice", "double", "half", "x times") that the material doesn't state;
- a number given the wrong meaning (a level stated as a difference, a "with" value as a gap);
- a claim about how or when a player is used that the material doesn't show, or that a chart contradicts;
- a metric described as a different one (runs saved or above average is never "win probability" or "chance of
  winning"; Impact is never runs saved; a strike rate is never an average);
- a statement that contradicts THE VERDICT (a flat yes/no when it is "Partly" or "Inconclusive");
- blaming a player, or hype ("game-changer", "elite", "unmatched").
Not problems: restating a chart's title or help line in other words (titles are verified facts computed from the data);
a number rounded the way the title or help line rounds it; for balls per wicket, economy and averages, lower is better;
fair framing such as "raises questions", "is it worth it?", "slightly", "mixed"; the closing question.

Material:
%(material)s

Voiceover:
%(script)s
"""


def chart_text(c: Dict[str, Any]) -> str:
    """A chart as text for the checker: title, help line, and its rows' values (so "only X is under 30" can be
    checked against every row, not just the headline)."""
    p = c.get("payload") or {}
    rows = []
    for r in (p.get("rows") or [])[:10]:
        if not isinstance(r, dict):
            continue
        name = r.get("name") or r.get("label") or r.get("short") or ""
        vals = {k: v for k, v in r.items() if k in ("value", "subject", "field") or k == "values"}
        rows.append(f"{name}: {json.dumps(vals, default=str)}")
    return (f"Chart: {c.get('title', '')}. {c.get('help', '')}"
            + (f" Rows: {'; '.join(rows)}" if rows else ""))


def check(sc: Dict[str, Any], hook: str, bs: List[Tuple[int, Dict[str, Any]]], notes: str) -> Optional[str]:
    """None if a second reading finds every claim supported by the cards, else the problems."""
    material = "\n".join([f"Post hook: {hook}"] + [f"Chart {i + 1}: " + chart_text(c) for i, (_, c) in enumerate(bs)]
                         + ([notes] if notes else []))
    resp = _client().chat.completions.create(
        model=SCRIPT_MODEL, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "user", "content": CHECK % {"material": material,
                                                        "script": "\n".join([f"Hook: {sc['hook']}"] + [
                                                            f"Line {i + 1}: {l}" for i, l in enumerate(sc["lines"])])}}])
    got = json.loads(resp.choices[0].message.content or "{}")
    problems = [p for p in (got.get("problems") or []) if isinstance(p, str) and p.strip()]
    return "; ".join(problems) if problems else None


def script(hook: str, bs: List[Tuple[int, Dict[str, Any]]], notes: str = "", length: str = "short",
           close: str = "") -> Tuple[Dict[str, Any], str]:
    """(script, source): the model's when it passes the guard (one retry), else the template's. notes: the post's text
    slides, whose numbers may be voiced too."""
    ok = allowed(hook, bs) | numbers(notes) | {_short(n) for n in numbers(notes)}
    why = ""
    for _ in range(4):
        try:
            s = script_llm(hook, bs, why, notes, length, close)
        except Exception as exc:  # no key, network: the template
            logger.warning("reel script: %r", exc)
            break
        why = guard(s, ok, len(bs), LENGTHS[length]["words"]) or ""
        if not why:
            try:
                why = check(s, hook, bs, notes) or ""
            except Exception as exc:  # the check couldn't run: don't ship an unchecked script
                why = f"check failed: {exc!r}"[:200]
        if not why:
            return s, SCRIPT_MODEL
        logger.info("reel script rejected: %s", why)
    return template(hook, bs), "template"


# ---- voice ----------------------------------------------------------------------------------------------------------

def pronunciations() -> Dict[str, Dict[str, str]]:
    """Names the voice says differently from how they're spelled (services/reel_pronounce.py)."""
    from services.reel_pronounce import PRONOUNCE

    return PRONOUNCE


def hints(text_: str) -> str:
    """Pronunciation notes for the names in a script, for the voice's instructions."""
    return " ".join(v["hint"] for k, v in pronunciations().items() if v.get("hint") and k in text_)


def spoken(text_: str) -> str:
    """What the voice reads: names respelled (reel_pronounce.py), signs as words ("−0.29" -> "minus 0.29")."""
    for name, v in pronunciations().items():
        if v.get("say") and v["say"] != name:
            text_ = re.sub(rf"\b{re.escape(name)}\b", v["say"], text_)
    text_ = re.sub(r"(?<![\w.])[−–-](?=\d)", "minus ", text_)
    return re.sub(r"\+(?=\d)", "plus ", text_)


def tts(text_: str, voice: str, out: Path) -> float:
    resp = _client().audio.speech.create(model=TTS_MODEL, voice=voice, input=spoken(text_),
                                         instructions=(TONE + " " + hints(text_)).strip(),
                                         response_format="mp3")
    raw = out.with_suffix(".raw.mp3")
    raw.write_bytes(resp.read() if hasattr(resp, "read") else resp.content)
    if abs(TEMPO - 1) > 0.01:  # a touch quicker: Reels reward pace
        _ff([shutil.which("ffmpeg"), "-y", "-loglevel", "error", "-i", str(raw), "-filter:a", f"atempo={TEMPO}", str(out)])
    else:
        raw.replace(out)
    return duration(out)


def duration(path: Path) -> float:
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True, check=True)
    return float(probe.stdout.strip())


# ---- captions -------------------------------------------------------------------------------------------------------

def caption_chunks(line: str, start: float, length: float, per: int = CAPTION_WORDS) -> List[Tuple[float, float, str]]:
    """(from, to, text): the line a few words at a time, each on screen for its share of the line's characters."""
    words = line.split()
    chunks = [" ".join(words[i:i + per]) for i in range(0, len(words), per)]
    total = sum(len(c) + 1 for c in chunks) or 1
    out, t = [], start
    for c in chunks:
        d = length * (len(c) + 1) / total
        out.append((round(t, 3), round(t + d, 3), c))
        t += d
    return out


def balance(text_: str, width: int = 24) -> List[str]:
    """One line, or two split at the word break nearest the middle (no stranded "0.02.")."""
    if len(text_) <= width:
        return [text_]
    ws = text_.split()
    best = min(range(1, len(ws)), key=lambda k: abs(len(" ".join(ws[:k])) - len(" ".join(ws[k:]))))
    return [" ".join(ws[:best]), " ".join(ws[best:])]


def wrap(text_: str, width: int) -> str:
    lines, cur = [], ""
    for w in text_.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


# ---- compose --------------------------------------------------------------------------------------------------------

def _ff(args: List[str], timeout: int = 600) -> None:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg: {proc.stderr.strip()[-600:]}")


def record(carousel_id: str, numbers_: List[int], out: Path, base: str) -> Dict[str, Any]:
    proc = subprocess.run(["node", str(ROOT / "scripts/record_ig_beats.mjs"), carousel_id, ",".join(map(str, numbers_)),
                           str(out), "--base", base, "--fps", str(FPS)],
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-400:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _drawtext(textfile: Path, font: Path, size: int, y: str, start: float, end: float, color: str = "white",
              box: bool = False) -> str:
    # expansion=none: text is drawn as written ("86%" would otherwise be read as a format code and the line dropped).
    f = (f"drawtext=fontfile='{font}':textfile='{textfile}':expansion=none:fontsize={size}:fontcolor={color}:line_spacing=10"
         f":x=(w-text_w)/2:y={y}:enable='between(t,{start:.3f},{end:.3f})'")
    if box:
        f += ":box=1:boxcolor=black@0.55:boxborderw=18"
    return f


def compose(tmp: Path, beat_frames: List[Path], durations: List[float], voice: Path,
            captions: List[Tuple[float, float, str]], hook_text: str, hook_end: float, out: Path,
            cover: Optional[Path] = None) -> float:
    """The Reel: each beat's reveal frames, then its finished frame held for its duration; the voice (one take) under
    them with a quiet bed; the hook above the slide until the story moves on, then the brand; timed captions below."""
    ffmpeg = shutil.which("ffmpeg")
    clips = []
    lead = 0.0
    if cover is not None and COVER_SECONDS > 0 and durations and durations[0] > COVER_SECONDS + 1:
        # The carousel's first slide for a moment (the voice already going), so it's the frame offered as the cover;
        # the first beat gives up that time, so everything after stays where the voice put it.
        clip = tmp / "cover.mp4"
        _ff([ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-t", f"{COVER_SECONDS:.3f}", "-i", str(cover),
             "-vf", f"scale={W}:{SLIDE_H},pad={W}:{H}:0:{TOP}:color={BG},setsar=1,fps={FPS},format=yuv420p",
             "-t", f"{COVER_SECONDS:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(clip)], timeout=120)
        clips.append(clip)
        lead = COVER_SECONDS
        durations = [durations[0] - lead] + list(durations[1:])
    for i, (frames, secs) in enumerate(zip(beat_frames, durations)):
        clip = tmp / f"beat{i}.mp4"
        n = len(list(frames.glob("*.png")))
        hold = max(0.0, secs - n / FPS)
        _ff([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%03d.png"),
             "-vf", f"scale={W}:{SLIDE_H},tpad=stop_mode=clone:stop_duration={hold:.3f},"
                    f"pad={W}:{H}:0:{TOP}:color={BG},setsar=1,fps={FPS},format=yuv420p",
             "-t", f"{secs:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(clip)], timeout=300)
        clips.append(clip)
    listing = tmp / "clips.txt"
    listing.write_text("".join(f"file '{c}'\n" for c in clips))
    video = tmp / "video.mp4"
    _ff([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(video)])
    total = sum(durations) + lead

    hook_file = tmp / "hook.txt"
    hook_file.write_text(wrap(hook_text, 26))
    brand = tmp / "brand.txt"
    brand.write_text("HINDSIGHT  ·  hindsightcricket.com")
    # The top band carries the brand throughout; the hook is captioned at the bottom like every other line.
    draws = [_drawtext(brand, FONT_BODY, 34, f"({TOP}-text_h)/2", lead, total + 1, color="0xb6f24a")]
    # No captions over the cover frame (it's the post's cover); from then on every line, the hook included.
    captions = [(max(a, lead), b, c) for a, b, c in captions if b > lead + 0.05]
    for i, (a, b, c) in enumerate(captions):
        # Fixed positions (not centred on each phrase's own height), so the text never bobs; a long phrase is split
        # near its middle into two lines, each centred.
        for k, line in enumerate(balance(c)):
            f = tmp / f"cap{i}_{k}.txt"
            f.write_text(line)
            draws.append(_drawtext(f, FONT_BOLD, 58, str(TOP + SLIDE_H + 60 + 72 * k), a, b))
    filt = (f"[0:v]{','.join(draws)},fade=t=out:st={max(0, total - 0.35):.2f}:d=0.35[v];"
            # a soft pad under the voice: low sines, slowly swelling, well below it
            f"aevalsrc='0.5*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.25*t))+0.35*sin(2*PI*164.8*t)+0.25*sin(2*PI*220*t)':"
            f"s=44100:d={total:.2f},lowpass=f=900,volume=0.05,afade=t=in:d=0.6,afade=t=out:st={max(0, total - 0.8):.2f}:d=0.8,"
            f"aformat=channel_layouts=stereo[bed];[1:a]aformat=sample_rates=44100:channel_layouts=stereo,apad[vo];"
            f"[vo][bed]amix=inputs=2:duration=shortest,volume=2[a]")
    _ff([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-i", str(voice), "-filter_complex", filt,
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)])
    return round(total, 2)


def words_timed(audio: Path) -> List[Dict[str, float]]:
    """[{word, start, end}] for the voice, from OpenAI's transcription (we know the text; this only times it)."""
    with open(audio, "rb") as f:
        resp = _client().audio.transcriptions.create(model="whisper-1", file=f, response_format="verbose_json",
                                                     timestamp_granularities=["word"])
    return [{"word": w.word, "start": float(w.start), "end": float(w.end)} for w in (getattr(resp, "words", None) or [])]


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("−", "minus").replace("+", "plus"))


#: Words a caption phrase shouldn't end on: the phrase carries on to the word they lead into.
WEAK = {"a", "an", "the", "of", "to", "in", "on", "at", "for", "from", "with", "without", "against", "and", "but", "or",
        "is", "are", "was", "his", "her", "their", "its", "india's", "than", "just", "only", "per", "by", "as", "top"}


def phrases(words: List[str], most: int = 6, chars: int = 32, hard: int = 40) -> List[Tuple[int, int]]:
    """[(first word, end)] caption phrases: break after punctuation, or once a phrase reaches `most` words or `chars`
    characters, but not after a small word ("against", "the"), unless it would pass `hard` characters; a lone last
    word joins the phrase before it."""
    out, start = [], 0
    for i, w in enumerate(words):
        length = len(" ".join(words[start:i + 1]))
        ends = w.endswith((",", ".", "?", "!", ";", ":"))
        full = i + 1 - start >= most or length >= chars
        weak = w.lower().strip(",.?!;:") in WEAK
        if ends or (full and (not weak or length >= hard)):
            out.append((start, i + 1))
            start = i + 1
    if start < len(words):
        out.append((start, len(words)))
    # A one-word phrase ("without.") joins the phrase before it when the two still fit.
    merged: List[Tuple[int, int]] = []
    for a, b in out:
        if merged and b - a == 1 and len(" ".join(words[merged[-1][0]:b])) <= 48:  # two caption lines
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return merged


def word_times(ours: List[str], timed: List[Dict[str, float]], total: float) -> List[float]:
    """When each of our words starts: matched to the transcription's words where they agree (difflib), the rest placed
    between their matched neighbours (a number we write as one word can be several spoken)."""
    import difflib

    n = len(ours)
    if not timed:
        chars = [sum(len(w) + 1 for w in ours[:j]) for j in range(n)]
        whole = max(1, sum(len(w) + 1 for w in ours))
        return [total * c / whole for c in chars]
    a, b = [_norm(w) for w in ours], [_norm(w["word"]) for w in timed]
    t: List[Optional[float]] = [None] * n
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            t[blk.a + k] = timed[blk.b + k]["start"]
    t[0] = 0.0 if t[0] is None else t[0]
    for j in range(n):  # fill gaps by interpolating between known neighbours
        if t[j] is None:
            prev = j - 1
            nxt = next((k for k in range(j + 1, n) if t[k] is not None), None)
            hi = t[nxt] if nxt is not None else total
            span = (nxt if nxt is not None else n) - prev
            t[j] = t[prev] + (hi - t[prev]) / span
    out, last = [], 0.0
    for v in t:  # never earlier than the word before
        last = max(last, v)
        out.append(last)
    return out


def align(segments: List[str], timed: List[Dict[str, float]], total: float,
          per: int = CAPTION_WORDS) -> Tuple[List[float], List[Tuple[float, float, str]]]:
    """(each segment's start, captions) for the script's segments spoken in one take. Every word is timed from the
    transcription (word_times); captions are phrases (phrases), each on screen from its first word until the next
    phrase starts, so the text changes with the voice, not on a fixed count."""
    ours = [w for seg in segments for w in seg.split()]
    if not ours:
        return [0.0] * len(segments), []
    at = word_times(ours, timed, total)
    starts, caps, j = [], [], 0
    bounds = []
    for seg in segments:
        ws = seg.split()
        starts.append(0.0 if j == 0 else at[j])
        bounds += [(j + a, j + b) for a, b in phrases(ws)]
        j += len(ws)
    for i, (a, b) in enumerate(bounds):
        end = at[bounds[i + 1][0]] if i + 1 < len(bounds) else total
        caps.append((round(at[a], 3), round(max(end, at[a] + 0.3), 3), " ".join(ours[a:b])))
    return starts, caps


def srt(captions: List[Tuple[float, float, str]], offset: float = 0.0) -> str:
    """The captions as a SubRip file, for YouTube Studio's subtitles upload."""
    def ts(x: float) -> str:
        ms = int(round((x + offset) * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    return "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(captions, 1))


def first_slide(carousel_id: str, tmp: Path) -> Optional[Path]:
    """The carousel's rendered first slide (ig_slide_images), or None if it isn't rendered yet."""
    from sqlalchemy import text

    from database import engine

    with engine.connect() as conn:
        png = conn.execute(text("SELECT png FROM ig_slide_images WHERE carousel_id = :c AND n = 1"), {"c": carousel_id}).scalar()
    if not png:
        return None
    f = tmp / "cover.png"
    f.write_bytes(bytes(png))
    return f


def make(carousel_id: str, slides: List[Dict[str, Any]], voice: Optional[str] = None, base: str = SITE,
         store: bool = True, out: Optional[Path] = None, plan: Optional[Dict[str, Any]] = None,
         length: str = "short") -> Optional[Dict[str, Any]]:
    """Build the v2 Reel. plan: a script already made (the same script in several voices); else one is written.
    length: "short" (about 25-30s) or "long" (45-60s, up to 5 charts)."""
    if not shutil.which("ffmpeg"):
        return None
    hook = next((s.get("text") for s in slides if s.get("type") == "hook"), "") or ""
    bs = beats(slides, k=LENGTHS[length]["beats"])
    if plan and plan.get("beats"):  # beats chosen by hand (scripts/make_reel_v2.py --beats)
        bs = [(n, slides[n - 1]["card"]) for n in plan["beats"]]
    if len(bs) < 2:
        return None
    if plan is None or not plan.get("script"):
        sc, source = script(hook, bs, notes_of(slides), length, (plan or {}).get("close", ""))
        plan = {"script": sc, "source": source, "beats": [n for n, _ in bs], "length": length}
    sc, voice = plan["script"], voice or VOICE
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        got = record(carousel_id, plan["beats"], tmp / "frames", base)
        if got.get("failed"):
            raise RuntimeError(f"recording failed: {got['failed']}")
        # One take: the whole story spoken at once, so it flows; then timed, so each chart arrives with its line.
        segments = [sc["hook"], *sc["lines"]]
        voice_file = tmp / "voice.mp3"
        spoken_len = tts(" ".join(segments), voice, voice_file)
        try:
            timed = words_timed(voice_file)
        except Exception as exc:  # no transcription: share the time out by characters
            logger.warning("reel timing: %r", exc)
            timed = []
        starts, captions = align(segments, timed, spoken_len)
        hook_end = starts[1]
        # Beat 1 carries the hook and its line; each other beat starts with its line. A short tail after the last word.
        cuts = [0.0] + starts[2:] + [spoken_len + 0.6]
        durations = [round(b - a, 3) for a, b in zip(cuts, cuts[1:])]
        mp4 = out or (tmp / "reel.mp4")
        subtitles = srt(captions)
        cover = first_slide(carousel_id, tmp)
        seconds = compose(tmp, [tmp / "frames" / str(n) for n in plan["beats"]], durations, voice_file, captions,
                          sc["hook"], hook_end, mp4, cover=cover)
        if seconds > MAX_SECONDS:
            logger.warning("reel v2 for %s is %.1fs", carousel_id, seconds)
        if store:
            from sqlalchemy import text

            from database import engine

            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO ig_reels (carousel_id, mp4, seconds) VALUES (:c, :m, :s)
                    ON CONFLICT (carousel_id) DO UPDATE SET mp4 = EXCLUDED.mp4, seconds = EXCLUDED.seconds, made_at = now()
                """), {"c": carousel_id, "m": mp4.read_bytes(), "s": seconds})
    return {"seconds": seconds, "script": sc, "source": plan["source"], "voice": voice, "beats": plan["beats"],
            "length": plan.get("length", length), "srt": subtitles,
            "mp4": str(out) if out else None}


# ---- the A/B, and the queue ------------------------------------------------------------------------------------------

def variant(kind: str, day: Optional[date]) -> str:
    """'v2' or 'v1' for a post: v2 only when switched on (REEL_V2=1) and the kind suits it; during the A/B (REEL_AB=1)
    alternate days (even ordinals v2), so the two are compared on similar posts."""
    if os.getenv("REEL_V2") != "1" or kind not in ELIGIBLE:
        return "v1"
    if os.getenv("REEL_AB", "1") == "1" and day is not None and day.toordinal() % 2:
        return "v1"
    return "v2"


def for_carousel(carousel_id: str) -> Optional[float]:
    """The v2 Reel for a queued post's carousel when its variant is v2 (the result goes on facts.reel); None otherwise,
    and on any failure, so the caller makes the v1 Reel."""
    from sqlalchemy import text

    from database import engine
    from services.ig_plan import _kind

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, angle_key, source, pillar, planned_for, facts FROM content_packs
            WHERE channel = 'instagram' AND facts->>'carousel_id' = :c ORDER BY id DESC LIMIT 1
        """), {"c": carousel_id}).mappings().first()
        snap = conn.execute(text("SELECT data FROM chart_snapshots WHERE id = :c"), {"c": carousel_id}).scalar() or {}
    if not row:
        return None
    v = variant(_kind(dict(row)), row["planned_for"])
    info: Dict[str, Any] = {"variant": v}
    seconds = None
    if v == "v2":
        try:
            made = make(carousel_id, snap.get("slides") or [])
        except Exception as exc:  # pragma: no cover - a Reel never blocks a post: v1 instead
            logger.exception("reel v2 for %s failed", carousel_id)
            made, info = None, {"variant": "v1", "v2_error": str(exc)[:200]}
        if made:
            seconds = made["seconds"]
            info.update(script=made["script"], source=made["source"], voice=made["voice"], beats=made["beats"],
                        seconds=seconds, length=made.get("length"), srt=made.get("srt"))
    with engine.begin() as conn:
        conn.execute(text("UPDATE content_packs SET facts = jsonb_set(COALESCE(facts, '{}'::jsonb), '{reel}', CAST(:r AS jsonb)) "
                          "WHERE id = :i"), {"r": json.dumps(info), "i": row["id"]})
        if seconds:
            from services.ig_captions import with_ai_voice

            cap = conn.execute(text("SELECT caption FROM content_packs WHERE id = :i"), {"i": row["id"]}).scalar()
            conn.execute(text("UPDATE content_packs SET caption = :c WHERE id = :i"),
                         {"c": with_ai_voice(cap or ""), "i": row["id"]})
    return seconds

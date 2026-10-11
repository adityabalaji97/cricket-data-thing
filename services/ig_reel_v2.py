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
SCRIPT_MODEL = "gpt-4o-mini"
#: How the voice speaks (gpt-4o-mini-tts instructions): REEL_TONE overrides it, like REEL_VOICE, without a deploy.
TONE = os.getenv("REEL_TONE") or ("Brisk, confident cricket analyst on a highlights show: a quick, lively pace. "
                                  "Conversational, energetic but not shouty; land each number clearly; slight lift on the hook.")
FPS = 30
W, H, SLIDE_H, TOP = 1080, 1920, 1350, 285
BG = "0x0a0c11"
GAP = 0.12                     # seconds of silence between lines
WORDS = (28, 56)               # a script's word count must sit in this range (about 15-25 seconds spoken; 30 max)
MAX_SECONDS = 30
CAPTION_WORDS = 3              # words on screen at a time
ELIGIBLE = ("recap", "spotlight", "record", "trend", "debate", "weird", "myth")
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
        f = float(v)
        return [str(int(round(f))), f"{f:.1f}", f"{f:.2f}", f"{abs(f):.0f}", f"{abs(f):.1f}", f"{abs(f):.2f}"]
    return [str(v)]


def allowed(hook: str, bs: List[Tuple[int, Dict[str, Any]]]) -> set:
    """Every number the script may say: those in the hook, the beats' titles and help lines, and their chart values."""
    text_ = " ".join([hook] + [f"{c.get('title', '')} {c.get('help', '')}" for _, c in bs])
    nums = numbers(text_)
    for _, c in bs:
        nums |= numbers(" ".join(_flatten(c.get("payload"))))
    return nums | {_short(n) for n in nums}


def guard(script: Dict[str, Any], ok: set, k: int) -> Optional[str]:
    """None if the script is usable, else why not."""
    lines = script.get("lines")
    if not isinstance(script.get("hook"), str) or not isinstance(lines, list) or len(lines) != k:
        return "shape"
    words = len(" ".join([script["hook"], *lines]).split())
    if not WORDS[0] <= words <= WORDS[1]:
        return f"{words} words"
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


PROMPT = """You write the voiceover for a 15-20 second Instagram Reel about cricket data.
Return JSON: {"hook": string, "lines": [string, ...]} with exactly %(k)d lines, one per chart, in the order given.
Rules:
- 35 to 50 words in total (15-25 seconds spoken). Spoken English, short sentences.
- The hook comes first and must grab in the first 2 seconds. Base it on the post hook below, keeping its key number and
  name, in under 10 words.
- Each line says what its chart shows, in one short sentence.
- Use ONLY numbers that appear in the material below, written as digits exactly as given (e.g. 85%%, 1,024, 0.27).
  Never round, combine, or compute new numbers. If unsure, leave the number out.
- Don't blame players; describe what happened. No hashtags, no emojis, no "in this video".
- End the last line with a short question or a punchy closer that makes people want to comment or rewatch.

Post hook: %(hook)s

Charts:
%(charts)s
"""


def script_llm(hook: str, bs: List[Tuple[int, Dict[str, Any]]], feedback: str = "") -> Dict[str, Any]:
    charts = "\n".join(f"{i + 1}. {c.get('title', '')}" + (f" ({c['help']})" if c.get("help") else "")
                       for i, (_, c) in enumerate(bs))
    msg = PROMPT % {"k": len(bs), "hook": hook, "charts": charts}
    if feedback:
        msg += f"\nYour last attempt was rejected ({feedback}). Fix that."
    resp = _client().chat.completions.create(model=SCRIPT_MODEL, temperature=0.6,
                                             response_format={"type": "json_object"},
                                             messages=[{"role": "user", "content": msg}])
    return json.loads(resp.choices[0].message.content or "{}")


def script(hook: str, bs: List[Tuple[int, Dict[str, Any]]]) -> Tuple[Dict[str, Any], str]:
    """(script, source): the model's when it passes the guard (one retry), else the template's."""
    ok = allowed(hook, bs)
    why = ""
    for _ in range(2):
        try:
            s = script_llm(hook, bs, why)
        except Exception as exc:  # no key, network: the template
            logger.warning("reel script: %r", exc)
            break
        why = guard(s, ok, len(bs)) or ""
        if not why:
            return s, SCRIPT_MODEL
        logger.info("reel script rejected: %s", why)
    return template(hook, bs), "template"


# ---- voice ----------------------------------------------------------------------------------------------------------

def tts(text_: str, voice: str, out: Path) -> float:
    resp = _client().audio.speech.create(model=TTS_MODEL, voice=voice, input=text_, instructions=TONE,
                                         response_format="mp3")
    out.write_bytes(resp.read() if hasattr(resp, "read") else resp.content)
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
    f = (f"drawtext=fontfile='{font}':textfile='{textfile}':fontsize={size}:fontcolor={color}:line_spacing=10"
         f":x=(w-text_w)/2:y={y}:enable='between(t,{start:.3f},{end:.3f})'")
    if box:
        f += ":box=1:boxcolor=black@0.55:boxborderw=18"
    return f


def compose(tmp: Path, beat_frames: List[Path], segs: List[Dict[str, Any]], hook_text: str, out: Path) -> float:
    """segs: one per beat {"audio": [mp3, ...], "lines": [text, ...], "seconds": total}; the first holds the hook too."""
    ffmpeg = shutil.which("ffmpeg")
    # 1. Each beat: its reveal frames, then the finished frame held, on the 9:16 canvas.
    clips = []
    for i, (frames, seg) in enumerate(zip(beat_frames, segs)):
        clip = tmp / f"beat{i}.mp4"
        n = len(list(frames.glob("*.png")))
        hold = max(0.0, seg["seconds"] - n / FPS)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%03d.png"),
                        "-vf", f"scale={W}:{SLIDE_H},tpad=stop_mode=clone:stop_duration={hold:.3f},"
                               f"pad={W}:{H}:0:{TOP}:color={BG},setsar=1,fps={FPS},format=yuv420p",
                        "-t", f"{seg['seconds']:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(clip)],
                       check=True, capture_output=True, timeout=300)
        clips.append(clip)
    listing = tmp / "clips.txt"
    listing.write_text("".join(f"file '{c}'\n" for c in clips))
    video = tmp / "video.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
                    str(video)], check=True, capture_output=True, timeout=300)
    total = sum(s["seconds"] for s in segs)

    # 2. The voice: every line in order, a short gap after each.
    voice_parts, t, captions = [], 0.0, []
    hook_end = None
    for seg in segs:
        for mp3, line in zip(seg["audio"], seg["lines"]):
            d = duration(mp3)
            captions += caption_chunks(line, t, d)
            if hook_end is None:
                hook_end = t + d
            voice_parts.append((mp3, d))
            t += d + GAP
    vlist = tmp / "voice.txt"
    silence = tmp / "gap.mp3"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono", "-t", str(GAP),
                    "-c:a", "libmp3lame", str(silence)], check=True, capture_output=True)
    vlist.write_text("".join(f"file '{p}'\nfile '{silence}'\n" for p, _ in voice_parts))
    voice = tmp / "voice.wav"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(vlist), "-ar", "44100",
                    "-ac", "2", str(voice)], check=True, capture_output=True, timeout=120)

    # 3. Text: the hook above the slide while it's spoken, then the brand; captions below, in step with the voice.
    hook_file = tmp / "hook.txt"
    hook_file.write_text(wrap(hook_text, 26))
    brand = tmp / "brand.txt"
    brand.write_text("HINDSIGHT  ·  hindsightcricket.com")
    draws = [_drawtext(hook_file, FONT_BOLD, 66, f"({TOP}-text_h)/2", 0, hook_end or 2.5),
             _drawtext(brand, FONT_BODY, 34, f"({TOP}-text_h)/2", hook_end or 2.5, total + 1, color="0xb6f24a")]
    for i, (a, b, c) in enumerate(captions):
        f = tmp / f"cap{i}.txt"
        f.write_text(c)
        draws.append(_drawtext(f, FONT_BOLD, 64, f"{TOP + SLIDE_H}+({H - TOP - SLIDE_H}-text_h)/2", a, b))
    filt = (f"[0:v]{','.join(draws)},fade=t=out:st={max(0, total - 0.35):.2f}:d=0.35[v];"
            # a soft pad under the voice: two low sines, slowly swelling, well below it
            f"aevalsrc='0.5*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.25*t))+0.35*sin(2*PI*164.8*t)+0.25*sin(2*PI*220*t)':"
            f"s=44100:d={total:.2f},lowpass=f=900,volume=0.05,afade=t=in:d=0.6,afade=t=out:st={max(0, total - 0.8):.2f}:d=0.8,"
            f"aformat=channel_layouts=stereo[bed];[1:a]volume=1.0[vo];[vo][bed]amix=inputs=2:duration=first,volume=2[a]")
    _ff([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-i", str(voice), "-filter_complex", filt,
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)])
    return round(total, 2)


def make(carousel_id: str, slides: List[Dict[str, Any]], voice: Optional[str] = None, base: str = SITE,
         store: bool = True, out: Optional[Path] = None, plan: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Build the v2 Reel. plan: a script already made (the same script in several voices); else one is written."""
    if not shutil.which("ffmpeg"):
        return None
    hook = next((s.get("text") for s in slides if s.get("type") == "hook"), "") or ""
    bs = beats(slides)
    if len(bs) < 2:
        return None
    if plan is None:
        sc, source = script(hook, bs)
        plan = {"script": sc, "source": source, "beats": [n for n, _ in bs]}
    sc, voice = plan["script"], voice or VOICE
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        got = record(carousel_id, plan["beats"], tmp / "frames", base)
        if got.get("failed"):
            raise RuntimeError(f"recording failed: {got['failed']}")
        segs = []
        lines = [sc["hook"], *sc["lines"]]
        clips = [tmp / f"line{i}.mp3" for i in range(len(lines))]
        secs = [tts(l, voice, c) for l, c in zip(lines, clips)]
        # The first beat carries the hook and its own line; each other beat its line.
        segs.append({"audio": clips[:2], "lines": lines[:2], "seconds": secs[0] + secs[1] + 2 * GAP})
        for i in range(2, len(lines)):
            segs.append({"audio": [clips[i]], "lines": [lines[i]], "seconds": secs[i] + GAP})
        mp4 = out or (tmp / "reel.mp4")
        seconds = compose(tmp, [tmp / "frames" / str(n) for n in plan["beats"]], segs, sc["hook"], mp4)
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
                        seconds=seconds)
    with engine.begin() as conn:
        conn.execute(text("UPDATE content_packs SET facts = jsonb_set(COALESCE(facts, '{}'::jsonb), '{reel}', CAST(:r AS jsonb)) "
                          "WHERE id = :i"), {"r": json.dumps(info), "i": row["id"]})
        if seconds:
            from services.ig_captions import with_ai_voice

            cap = conn.execute(text("SELECT caption FROM content_packs WHERE id = :i"), {"i": row["id"]}).scalar()
            conn.execute(text("UPDATE content_packs SET caption = :c WHERE id = :i"),
                         {"c": with_ai_voice(cap or ""), "i": row["id"]})
    return seconds

# Social copy, rewritten for each platform

The words around every post: Instagram captions, X threads, YouTube Shorts copy, Reel scripts. From a Fable advisor
review on 15 Nov 2026 of the copy code and the last 14 queued posts, against docs/social_rules.md and the house rules.

Status: **built** (15 Nov 2026), PR open.

## What the review found

- **Working:** covers, Reel hooks and the closing questions ("Who would you keep?") follow player + number and no-blame.
- **The first line is a method note.** Caption line 1, tweet 1 and the YouTube title often open on a deadline, "News
  first:" or a scope line, not the player and the number.
- **Lines read the slide back.** Thread and Reel lines repeat card titles instead of adding what the image can't show,
  and "+27.4" or "−0.08 wins" reach strangers unexplained.
- **Limits broken:** the CSK caption is 2,224 characters (Instagram caps at 2,200); #TopRightKohli carried 6 hashtags;
  YouTube titles are cut with "…"; hand-built posts get the same three generic YouTube tags.
- **X tags fight X:** the rules force the lead tag and #CricketTwitter on every tweet and a hashtag for every player's
  first mention (3-7 tags a tweet), while `ig_x.MAX_TAGS` says more than two reads as spam.
- **No alt text, no pinned YouTube comment.**

## Chunks

| # | Chunk | Status |
|---|---|---|
| S1 | Up to 4 images a tweet | [x] 15 Nov 2026: a tweet's `slides` (1-4 slide numbers; `slide` stays the first), `ig_x.hand_thread` takes a list, the admin shows and shares every image |
| S2 | X tags on tweet 1 only | [x] 15 Nov 2026: 1-2 tags on tweet 1, none after; player names in plain text; `thread_problems` and docs/social_rules.md (X) follow |
| S3 | Caption checks | [x] 15 Nov 2026: `social_rules.caption_problems`: over 2,200 characters, more than 5 tags, a first line without a number or over the 125-character fold, "News first"; shown with the slide warnings. House terms join the Reel hook's jargon list |
| S4 | YouTube copy | [x] 15 Nov 2026: a post's own `yt_title`; a title is never cut with "…" (the longest run of whole clauses within 60, else whole words); the description opens with the claim and the link; tags from the caption's own, not generic; a pinned comment (the caption's question + link) |
| S5 | Retention copy | [x] 15 Nov 2026: the hook first, the deadline and trade news after; "is down 0.79 wins", not "added −0.79"; under ±0.25 wins reads "about level" |
| S6 | Shared words | [x] 15 Nov 2026: `ig_captions.GLOSS`: one clause per measure (runs above par, wins added, Impact); the spotlight's default question becomes a pick-one |
| S7 | Alt text | [x] 15 Nov 2026: each slide's alt text (its title and top lines) stored with the post and shown in the admin |
| S8 | Reference decks | [x] 15 Nov 2026: a post marked `reference` (one slide per team, the SMAT round-ups) may run past 8 slides without a warning |

## Decisions

- **X hashtags (S2):** overturns the 7 Nov rule (player hashtags, lead tag + #CricketTwitter on every tweet). The
  advisor's case: hashtags add little reach on X now and "#CameronGreen cost ₹25.20 crore" reads worse than the name.
  Approved with the overhaul on 15 Nov 2026.
- **8 slides (S8):** kept for stories; reference decks are saved and sent, so they're exempt when marked.

## What changed (15 Nov 2026)

- `services/ig_x.py`: tweet 1 carries the caption's first one or two tags, later tweets none; names stay plain text;
  tweets carry `slides` (hand_thread takes a list of up to 4; `slide` is the first).
- `services/social_rules.py`: `thread_problems` checks tags after tweet 1, more than 4 images, length;
  `caption_problems` (length, tags, "News first", a first 125 characters without a number, a first sentence past the
  fold); house terms in `JARGON`; `REFERENCE_KINDS` skip the 8-slide warning.
- `services/ig_backlog.py`: `upsert_pack` adds caption warnings, stores `facts.alt` (`alt_texts`), and reads
  `facts.deck == "reference"`.
- `services/ig_notes.py`: `yt_title`, `youtube_copy` (own `yt_title`, claim + link first, specific tags, `pinned_comment`).
- `services/ig_captions.py`: `GLOSS`; spotlight question "Is he in your XI?". `services/ig_reel_v2.py` feeds GLOSS to
  the Reel writer.
- `articles/ipl-retention/post.py`: hook first in the caption, then the deadline and the news; tweet 1 player-first;
  `wins_tag` / `did` / `wins_short` read under ±0.25 as "about level"; the Reel defines wins added; "Send this to a
  Mumbai fan"; `yt_title` "MI retentions 2027: who should Mumbai keep?"; the hook player as a caption tag (#IPL dropped).
- `src/components/admin/IgPlanner.jsx`: up to 4 images a tweet (shared together), the pinned comment, alt text.
- docs/social_rules.md: X rewritten; new "Captions and YouTube" section; reference decks under Carousels.

Not done: the other article builders (articles/*/post.py) still write their own captions and tweet 1s; they pick up
the tag and YouTube changes through the shared code, and the caption check flags what's left when they're next run.

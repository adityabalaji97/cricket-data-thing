# Hindsight content guidelines

Rules for anything Hindsight publishes or hands to someone else to post: content packs, notes,
share images, titles. They come from a study of ~39,400 r/Cricket posts over 12 months plus 6
months each of r/ipl, r/IndianCricket, r/RCB, r/CricketShitpost and three team subreddits
(public archive, September 2026). **`services/content_rules.py` enforces the checkable parts in
code**; this file is the reasoning, for people and for any model writing Hindsight content.

## 1. Post a native image, never a link

| r/Cricket post type | share reaching the top 5% |
| --- | --- |
| Image | 9.9% |
| Video | 10.0% |
| News link | 5.2% |
| Text | 0.4% |
| YouTube | 0.2% |
| Tweet / X link | 0% |

- Every pack is **an image post**. The Hindsight link goes **only in the first comment** and as
  the image watermark, never as the post itself.
- Images are **1080×1350 (4:5)** by default: it fills the most of a phone feed on Reddit,
  Instagram and X. 1080×1080 for WhatsApp; 1200×630 only for link cards.

## 2. The title is the stat

- **A statement, never a question.** Statements reach the top 5% five times as often
  (5.6% vs 1.1%).
- **Include a number.** 6.4% vs 3.9%.
- **Long and self-contained, 60–200 characters.** 9.7% vs 2.9% for short titles. Someone who
  only reads the title should get the whole fact.
- **Lead with the player or team** the post is about.
- **Record / first / streak framing** where the facts support it: "the 3rd-highest ODI score
  since 2015", "first bowler since…", "longest streak…". Always with the comparison window.
- No clickbait ("insane", "you won't believe"), no ALL-CAPS words beyond acronyms, no "!!".
- **Every number in the title must come from the stored facts.** Code writes titles; a model may
  rephrase one only if the number check still passes.

## 3. Where to post

- **r/Cricket, "Stats" flair** for neutral records, internationals and cross-league facts: 16.7%
  of Stats posts reach the top 5%, behind only Awards and Milestone.
- **r/ipl** rewards moments and fan pride, not "Stats"/"OC"/"Analysis" (1.6–4%). IPL records
  still go to r/Cricket; a team-pride framing can go to that team's subreddit.
- **Country / team subreddits** (r/IndianCricket, r/RCB…) for facts that make that side look good.

## 4. When to post

- **12:00–18:00 UTC (17:30–23:30 IST)** is the best window.
- As close to the match as possible. Ball-by-ball data lands 1–2 days after a match, so a pack
  gets a **post-by deadline** (18:00 UTC, three days after the match, and never less than a day
  after the pack is made). Past it the pack is marked expired. Evergreen facts have no deadline.

## 5. Honesty

- Every image names its source and window ("Data as of 30 Sep 2026 · ball-by-ball"; "ODIs since
  2015"). Record claims state the comparison set and its size.
- Claims hold only within Hindsight's data. Say "since 2015" rather than "ever" unless the data
  covers the whole history.
- Never post from new accounts to get around a ban: Reddit treats it as ban evasion and can
  block the domain. Packs are for people posting from their own accounts.

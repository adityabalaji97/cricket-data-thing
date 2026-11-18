# Motion Reel build log

Running log for MOTION_REEL_PLAN.md (the plan and spec live untracked in the main checkout: `MOTION_REEL_PLAN.md`,
`docs/motion_reel_spec.md`, `docs/motion_reel_mockups/`). Everything here is uncommitted in this worktree.

## Done

### M1: Reel page, frame, recorder, safe-area check (17 Nov 2026)

- `src/components/ig/reel/IgReel.jsx`: `/ig/reel` (waits for `window.setReel(spec)`) and `/ig/:carouselId/reel`
  (spec from `snap.data.reel`). `window.renderAt(t)` sets t with `flushSync`; `data-reel-ready="true"` once the spec and
  fonts are in; `?t=12.5` shows one moment; `?guides=1` draws the keep-clear zones and the frame's reading boxes.
  Captions come from `spec.captions`, or from `spec.timing` (the finished Reels' timing.json shape) via
  `captionsFromTiming`, so an existing voice's word timestamps drive a Reel with no new TTS.
- `ReelFrame.jsx`: background, drifting glow in the scene's team colour, left stripe, chapter bars. No wordmark, no site
  name (decision 8). `Captions.jsx`: one line, spoken word in gold (`caption_colour: 'team'` uses the team's light tone).
- `SceneHost.jsx` + `scenes/index.js`: picks live scenes, the lift (in 0.35s up 60, out 0.3s up 80, 0.1s overlap),
  frame 0 never empty, the last scene never leaves; unknown kinds draw a placeholder.
- `scenes/HeroScene.jsx`: kind `hero` (decision 9): name at full size on frame 0, number counting (from `data.from`, so
  frame 0 is never a bare 0), second name + number + gold tag entering by 1.5s, scope line.
- `motion.js`: `u`, `clamp`, `lerp`, easings, `progress`, `countUp`, `countText`, `alpha`, `teamTone`, `activeScene`,
  `lift`, `activeCaption`, `captionsFromTiming`, `litAt`, `FRAME`, `frameBoxes`, `validateReel`, and the M2a primitives.
- `scripts/record_ig_reel.mjs`: `--spec`/`--id`, `--base`, `--fps`, `--from/--to`, `--stills`, `--mp4`, `--audio`
  (loudnorm as the finished Reels), `--format jpeg|png`, `--check`, `--guides`, `--port`. Frames are piped straight
  into ffmpeg (no frame files). `scripts/lib/cdp.mjs`: `screenshot(clip, { format, quality })`, PNG default.
- `scripts/dev/make_reel_fixture.py <team>`: retention spec from `articles/ipl-retention/<team>/slides.json`, numbers
  by path; hero real, the rest the carousel's own visuals on the storyboard's timings, captions at 3 words/s.
- `src/App.js`: the two routes, before `/ig/:carouselId/:n`.

### M2a: primitives, `motion` prop contract, fallback, every-kind test (17 Nov 2026)

- Primitives in `motion.js`: `reveal(m, i)`, `grow(m, i)`, `draw(m, from, dur)`, `deal(m, i)`, `ring(m, key)`,
  `camera(m, box)`, `countText(text, p)`, `enterSx`, `ringSx`. Each returns the finished state with no motion.
- Contract: `motion = { t, start, end, lit: {key, at} | null, plan }`; `MOTION_KINDS` (exported from
  `postVisuals.jsx`) lists kinds that read it. `scenes/VisualScene.jsx` plays any carousel kind: with motion if in
  `MOTION_KINDS`, else the fallback (left-to-right reveal 0.8s, then a slow camera push, or `scene.camera` region).
  Visuals are laid out at about a slide's content box (`VISUAL_ZOOM` 0.92 in an 876 x 920 box) so labels keep their
  carousel size.
- `everyKind.test.jsx`: every kind with a payload renders with and without motion; motion at its end equals the card's
  markup byte for byte; motion at t=0 renders; each motion kind actually changes mid-way; kinds with no payload are
  `test.todo` (22). Payloads: `__fixtures__/visual_payloads.json` (one per kind from posted carousels in `articles/`
  and the LOCAL `chart_snapshots`; 37 kinds) plus 5 hand-made.
- `motion.test.js`: helpers, captions, validateReel, and a grep that the reel folder has no transition / animation /
  timers / wall clock.

### M2b (part): motion in the common visuals + the round-2 Reel kinds (17 Nov 2026)

- Motion added (rows enter in reading order, bars grow from par/zero, values count, ring follows the voice):
  `metric_bars`, `share_bars`, `scorecard`, `bucket_bars`, `pair_dumbbell` (connector stretches a to b),
  `deep_compare` (rows flip in left/right alternately), `innings_scorecard`, `recap_text`, `percentile_strip` (dots
  slide from 0), and from visuals.jsx `stat`, `tiles` (dealt 0.35s apart, counting), `rank_bars`, `player_bars`, `dumbbell` (second end slides out).
- Reel-only kinds (`scenes/RoundScenes.jsx`): `hero_card`, `team_best`, `pool_count`, `pick_one` (send line one line,
  credit = the one brand mention, tiles breathe for the hold).
- `__fixtures__/smat_round2.reel.json`: the posted round-2 Reel as a spec (its data.js + timing.json).

## Decisions where the plan was ambiguous

- Frame y values: the finished Reels' (chapter bars y 370, kicker y 416, content from ~y 480, captions y 1504-1584),
  i.e. the spec's numbers +120, with the header reduced to the chapter bars (decision 8). Keep-clear bottom is y 1600+
  (decision 7 puts captions at ~1500-1580); top 0-200 and the right rail (x 940+, y 1000-1500) are unchanged.
- Beat times (`beats[].at`, `send.at`, `badge.at`, ...) are absolute seconds, so word timestamps drop straight in.
- Fonts are the site's (Barlow Semi Condensed / Barlow / IBM Plex Mono), not the finished Reels' Big Shoulders and
  IBM Plex Sans (plan decision 2 wins over the hand-built Reels).
- Caption lit word gold (M1 decision 7); the round-2 Reel used lime, the Dhoni Reel the team colour (option kept).
- `validateReel` flags captions over 30 characters (spec says 26; the posted Reels had 28-character lines).
- Ring in card visuals: the cards' own (2px outline in the brightest text); in Reel-only kinds the round-2 lime ring.

## Verification

- Stills: scratchpad `motion_build/m1_stills/contact.png` (MI fixture), `motion_build/r2_stills/` (round 2).
- `--check`: identical bytes for the same t rendered twice out of order (both specs).
- Video: `motion_build/r2_video/smat_round2_react.mp4`, 1080x1920, 30 fps, 31.4s, with the posted voice: 942 frames
  recorded in 56s (59 ms/frame, JPEG capture), under the 90s target.
- Tests: `CI=true npx react-scripts test --watchAll=false src/components/ig/reel src/components/story` (72 pass, 22
  todo). `react-scripts build` passes with no warnings in touched files.


### Round 2 (17 Nov 2026, after review)

- **Fonts before first frame:** IgReel loads every face/weight (`REEL_FACES`) for every character in the spec plus
  the glyphs the visuals write themselves (₹, ·, │, × ...): Google Fonts' unicode-range subsets load lazily on first
  use, which made a late scene's first frame differ (the reviewer's 29.5s still). Library CSS transitions (MUI's
  SvgIcon fill) are switched off inside the Reel root.
- **`--check`** now runs before stills, and its frames include each scene's first moment (start + 0.6s, late scenes
  first), so a first-use difference shows; differing pairs are saved as `check_<t>_1/2.png`. Both specs: identical.
  (With `--guides` one antialiased pixel can differ: debug overlay only.)
- **pick_one** is one flex column (question, sub, tiles, send, credit): no overlap at any question length. Tiles 410
  wide, breathe from their outer edges (never into the right rail). Send line and kicker shrink to fit one line
  (`fitSize`); `validateReel` flags kickers under 22px and send lines under 48px.
- **Null values:** `part(v, g)` keeps the value untouched once motion is done, so a null still prints "–".
- **Red below par, Reel only** (reviewer's call): `reelRed(motion, v)` in metric_bars, deep_compare, player_bars;
  `motion.plan.belowParRed: false` turns it off. Cards with no motion keep their colours. **Owner question:** should the
  carousel cards also draw below par in red (metric_bars, deep_compare, player_bars use slate/lime today)?
- **Fallback ring:** a beat may carry `box: {x, y, w, h}` (0..1 of the visual); fallback kinds ring that region.
- **Before/after carousel slides:** "Carousel not found" was environment, not code: main's :3000 dev server runs with
  `REACT_APP_API_URL` set to the production API (those ids exist only locally), and the local API's CORS allows only
  :3000. Checked instead with a baseline copy of HEAD (`git archive`) on :3200 and this worktree on :3100, both on
  the local API, in a headless Chrome with web security off: 26 slides from 5 local carousels (metric_bars,
  deep_compare, scorecard, innings_scorecard, pair_dumbbell, player_bars, share_bars, boundary_zones ...) are
  byte-identical. Screenshots: scratchpad `motion_build/slides/`.
- **M2b more kinds:** `xis` (dealt in batting order, sides alternating), `battles` (edge bar grows from the middle),
  `zone_pair` (wedges fill and count, left wheel then right), `pace_spin` (each phase's bar grows), `last_meeting`
  (win-probability line drawn, scores count). Strip: scratchpad `motion_build/kinds_a/contact.png`.

### Round 3 (17 Nov 2026)

- **`--check` correction:** round 2's log said "identical" but the `--guides` runs differed (a few antialiased pixels
  at the hero card's ring, frame 0.6). Fixes: the recorder now paints one throwaway frame after ready (the first paint
  could differ), and the guides draw with borders inside their boxes. Results
  (scratchpad `motion_build/chk_r3/check_results.txt`): without guides, identical on both specs, 3 of 3 repeat runs
  for round 2. With `--guides`, round 2 still differs at 0.6 in about 1 run in 2 (debug overlay only: recordings
  never use guides). MI with guides: identical.
- **Test check (reviewer's question):** `everyKind.test.jsx` asserts motion-at-end equals the card markup in full for
  every kind (with `plan.belowParRed: false`), not skipping rows; a separate test checks Reel-only red changes only
  a payload with a below-par row, and that null still prints "–".
- **pace_spin:** both the spin and the pace bars grow (already in round 2's last change).
- **M2b finished:** `par` (number counts, season line draws, dots land), `chase_band` (dot travels to the share, range
  fades in), `phase_diverging` (bars grow phase by phase; `DivergingBars` takes an optional `growRow`, default
  unchanged), `milestones` (one at a time, progress bars fill). `recent_results` wraps an external component
  (`VenueRecentMatches`) and plays the fallback.
- **M3a (boards and heat grids):** `squad_board` (chips dealt in reading order, ring on the voiced name),
  `grid_heat` (columns fill in innings order, cells 0.1s apart, numbers count, ring key "<row> · <column>"),
  `case_board` (cases one per `plan.case_every`, default 2.3s; in each, "for" from the left then "against" from the
  right, the same size), `template_board` (rows stamp 0.12s apart, dots travel to their place, ring on the role),
  `gap_fits` (roles, then their options). The MI fixture now carries voice beats for each (`make_reel_fixture.py`).
  Strips: `motion_build/kinds_b/contact.png`; whole Reel `motion_build/m1_stills3/contact.png`.
- **Decision 5 (five bowlers who bowl most per game)** is a data choice: `grid_heat` shows the payload's rows. The
  planner (M5) or the builder must pass those five; not done here.
- **For M5:** the fallback ring needs the planner to set a beat `box` ({x, y, w, h}, 0..1 of the visual) for kinds
  without motion; motion kinds take `key` only.
- **Not done in M3a:** `bowling_plan` (2 posted) still plays the fallback; `squad_board` doesn't yet zoom to a role
  row for big squads (spec section 3: establish, then push in): `scene.camera` can do it by hand.

### Round 4 (17 Nov 2026)

- **Decision 5, Reel only (reviewer's call):** `services/squad_view.py` keeps the carousel's grid exactly as before
  (six busiest by total balls; the loop is now `grid_rows()`, same output). New `regular_attack(players, n=5)`: the
  five who bowl the most per game (balls per bowling innings), best first, nobody left out of those five; used only
  by `build(db, code, reel=True)`, which adds `reel_bowling` (default off, so carousel and team page are unchanged).
  `tests/test_squad_view_attack.py` (3 tests). **Owner question:** should the carousel's grid also become the five
  who bowl most per game?
- **MI fixture refreshed:** `make_reel_fixture.py --attack <rows>` builds the Reel grid with `regular_attack` and
  squad_view's own cell maths (or reads `reel_bowling` from slides.json once a build writes it). Rows came from two
  read-only production queries (MI's bowlers, IPL 2025-26; scratchpad `motion_build/mi_attack_query.json`). MI's
  regular attack: Bumrah, Arshdeep, Bosch, Boult, Ghazanfar (Bosch and Ghazanfar are not in the carousel's six;
  Chahar, Thakur, Santner drop out). Bumrah, Arshdeep and Boult's cells match the carousel to the decimal.
- **Board push (spec section 3):** `VisualScene` measures marks the motion kinds key (`data-motion-key`, written only
  under motion) from the layout, and a board with 16+ keyed marks (`PUSH_MARKS`) or `scene.push` is shown whole for
  0.6s, then pushed in (1.6x) on the voiced chip, panning 0.5s between named chips, out over the last 0.5s; the view
  stays covered (no empty edge). squad_board keys its chips. Stills: `motion_build/m1_stills5/`.
- **Pages:** `scene.pages = {field, size, zoom, count?}` plays a board's list a page at a time at a readable zoom,
  each page the card's own drawing, its motion starting at the page start (beats on item names set page starts).
  MI fixture: case_board one call at a time (zoom 1.3); gap_fits only the voiced gap (zoom 1.12; at 1.3 its no-wrap
  line cropped).
- **DivergingBars** (shared site chart): `growRow` is optional; a test shows no `growRow` and a finished one draw the
  same markup, and the before/after slide check covers the carousels (`phase_diverging` appears on preview cards, not
  in the 5 local carousels compared).
- **`--check` flakiness fixed at the source:** the remaining 1-pixel differences came from scaled elements whose
  scale changed every frame (the hero cards' 1% breathing): Chrome reuses a layer's raster scale, so the result
  depended on the previous frame. The breathing is now a 2px vertical bob (translate only; the 0.6s settle still
  scales once). The recorder also does a warm-up pass (each scene once) and waits for fonts before recording.
  Result: 8 of 8 runs identical across both specs (`motion_build/chk_b_results.txt`).

### Round 5 (17 Nov 2026)

- **M3b, lines over time:** `win_prob_line` drives its own replay (`upto`) from the clock: the line draws ball by ball
  with its playhead dot and chance label, and each decisive over's band and line appear as the line reaches them.
  `race_lines`, `score_race`, `metric_lines`, `game_timeline`, `bid_trail`, `worm`, `elo_lines` draw left to right
  (`lineDraw`: the plot revealed at constant speed over `plan.draw` seconds, 2.5; the axis labels, or race_lines'
  names column, stay from the start). Not yet: key-moment markers popping on the voice, the pause at labelled turns.
- **M3b, scatter:** `scatter_plus`: the field fades in dim, the numbered players land one by one, then the subject's
  dot grows and his name appears; the ring follows the voice by name. Not yet: `totals_scatter`, `suits_scatter`,
  `twin_cloud`, `distance_star` (fallback).
- Strip: scratchpad `motion_build/kinds_c/contact.png` (and `kinds_c2/` for race_lines' names column).
- **Purity, again:** the fallback's slow push was a per-frame `scale`, which made Chrome's raster depend on the
  previous frame. It is now a 6px drift (translate); motion kinds have no camera unless `scene.camera` asks; the
  glow moves in whole canvas pixels; the glow and each scene are their own compositing layers (`will-change`).
  `--check` now measures any difference: headless Chrome still leaves a few antialiased pixels different between two
  draws of identical content (1-2 levels of 255, on SVG dashes and stroked circles), which it reports as "raster
  noise"; more than 200 pixels or a channel difference over 8 is a real difference. Results over 3 runs of 5 specs
  (`motion_build/chk_j_results.txt`): MI, round 2 and the M2b strip identical every run; the M3a strip once 3px of
  noise; the M3b strip 4-80px of noise (max difference 2) each run. No real difference.

- **Before/after carousel slides re-run after rounds 3-5** (baseline HEAD on :3200 v this worktree on :3100): the same 26 slides
  from 5 local carousels byte-identical (scratchpad `motion_build/slides2/`).

### Round 6 (17 Nov 2026)

- **Board push fixed (reviewer MUST 1):** the push now frames the voiced chip's whole group (a role's chips,
  `data-motion-group`, written only under motion) at a scale that fits it (at most 1.6, 94% of the width, 85% of the
  height), pans group to group, and the visual's box clips it (`overflow: hidden` while pushing or paging), so no chip
  is cut and nothing spills onto the kicker or the scope line. The role labels to the left of the chips can be out of
  frame while pushed. Stills: `motion_build/m1_stills6/`.
- **`--check` is strict again (reviewer MUST 2):** differences are compared per channel (rgb24, so a colour swap at
  the same brightness counts) with the pixel count, the largest channel difference and the bounding box. Raster noise
  is a difference of 1 level anywhere (seen: a whole area faded with group opacity, 1232px at 1 level) or up to 50
  pixels at 2-3 levels; anything else is a real difference. Files are named with t to 2 decimals. Two runs of 7 specs
  (`motion_build/chk_k_results.txt`): no real difference; noise only at 1-2 levels. The scatter_plus noise is one
  pixel at canvas (613, 870), a field dot mid-fade.
- **SVG charts:** a chart drawn as one SVG at 100% width keeps its aspect ratio, so narrowing its layout can't enlarge
  it. Line and scatter kinds now take the full box width (`KIND_ZOOM` 1.0, 8% larger than the slide's 0.92); filling
  the box to y 1440 would need taller charts in the components (not done: it would change the cards).
- **M3a finished:** `bowling_plan` fills over by over (0.1s an over, every row at once); the marked over's ring lands
  when the innings reaches it.
- **M3b finished:** `totals_scatter` (seasons' dots land in order), `suits_scatter` (players land one by one),
  `twin_cloud` (the cloud lands in its drawing order), `distance_star` (spokes grow out from the centre). Key moments:
  win_prob_line's bands, score_race's wicket dots and the timelines' marks appear as the line reaches them; marks
  popping on the voice's words is not done. Strip: `motion_build/kinds_d/`.
- **M3c (part):** `shot_wheel` (rays grow from the stumps over 1.6s), `ball_steps` (ball by ball, line and tag),
  `pitch_map` (cells land length by length), `sankey` (ribbons flow left to right). Strip: `motion_build/kinds_e/`.
  Left: `boundary_zones`, `innings_wagon`, `over_strips`, `pitch_usage`.

### Round 7 (17 Nov night, finished 18 Nov 2026)

- **Round-6 review fixes:**
  - squad_board push is anchored at the board's left edge, so the role labels are never cut, and frames the union
    of the voiced role's chips (its scale keeps their right edge in view, at most 1.6). Chips in other rows can still
    run off the right edge while pushed. Stills: `motion_build/m1_stills7/`.
  - twin_cloud and distance_star are laid out at zoom 1.3 (`KIND_ZOOM`). A constant outer `scale()` was tried first
    and dropped: it made `--check` flaky.
  - sankey: the draw keeps the first 10% (the first nodes) from the first frame, so no blank frame. The label overlaps
    ("Lost the toss" on its node bar, "Tied or no result" over the ribbons) are the card's own drawing (motion at its
    end draws the card's exact markup, at the slide's layout width), so they are left as a card issue to fix
    separately, not in the Reel.
- **M3c rest:** `over_strips` (overs fill in order, 0.1s each), `boundary_zones` (zones fill round the ground, shares
  counting), `pitch_usage` (cells fill length by length). `innings_wagon` wraps the game's `InningsClue` and plays
  the fallback. Strip: `motion_build/kinds_f/`.
- **`--check` on the M3c strip:** 3 runs: twin_cloud's frames (thin dots fading in) show 20-36px at up to 4 levels
  in 2 of 3 runs, and boundary_zones' 16.6s frame once 235px at up to 8 levels (semi-transparent wedges mid-fill).
  Raster-level, not t-dependence (same t, same DOM), but above the noise threshold. Open issue.

### Change A (owner's decision, 18 Nov 2026): below par draws red on the carousel cards too

- `postVisuals.jsx`: `belowPar(v)` replaces the Reel-only `reelRed(motion, v)`; `metric_bars` and `deep_compare`
  draw a below-par bar red on the card and in the Reel. `visuals.jsx` `player_bars`: a below-par bar is red at full
  opacity (it was its side colour at 35%). The every-kind test now compares motion-at-end with the card in full for
  every kind (no flag), and checks the card and the Reel draw a below-par row the same.
- Before/after (baseline HEAD on :3200 v this worktree on :3100, 26 slides from 5 local carousels, scratchpad
  `motion_build/slides3/`): 3 changed, each only by its below-par bars turning red: `8qHk6Zugu` slide 2 (metric_bars:
  KKR 2025-26 −13.1), `8qHk6Zugu` slide 4 (metric_bars: KKR 2018-23 −0.1, KKR 2025-26 −0.1), `YwJPBBJaN` slide 3
  (metric_bars: Axar Patel −28.4). The other 23 are byte-identical. Side by side:
  `motion_build/slides3/8qHk6Zugu/changed.png`, `motion_build/slides3/YwJPBBJaN/changed.png`.

### Change B (owner's decision, 18 Nov 2026): the carousel bowling grid is the regular attack

- `services/squad_view.py`: the bowling-by-phase card's rows are `regular_attack(players)` (the five who bowl most
  per game, best first), not the six busiest by total balls; the `reel=True` flag and `reel_bowling` are removed
  (carousel and Reel are the same grid). The title logic ("the only one of N above par") counts the five.
- `scripts/dev/make_reel_fixture.py`: uses the carousel's grid; warns when a slides.json predates the change (six
  rows) and no `--attack` file is given.
- Tests: `tests/test_squad_view_attack.py`, `test_squad_review.py`, `test_ipl_squads.py`, `test_social_rules.py`,
  `test_audit_social_rules.py`: 23 pass. Regression goldens were NOT run (they hit the main checkout's :8000). **Before
  merge: re-baseline the goldens** if any covers the team page's squad group (`/team-squad`), and rebuild the retention
  slides (`articles/ipl-retention/post.py`) to see the new grids.

### Round 8 (18 Nov 2026)

- **Change B, refined (reviewer):** `regular_attack` ranks by balls per match *played* (the most of his batting and
  bowling innings, or `games`), not per bowling innings, and a regular must have bowled in at least a third of the
  side's matches (the most any squad member played). A part-timer with three full spells no longer ranks first.
  Tests: `tests/test_squad_view_attack.py` (5, including that case). With the refined rule MI's grid is Bumrah,
  Arshdeep, Boult, Ghazanfar, Thakur (Bosch's 8 bowling innings fall under a third of 30).
- **Change A, extra coverage:** deep_compare before/after on two local carousels (`55wcevNCn` slide 6, `qNp3ZsddP`
  slide 3; scratchpad `motion_build/slides4/deep_compare_changed.png`): only the below-par bars turn red. The Rabada
  slide's highlighted −0.9 ("goes for 0.9 runs an over above par") is now a red bar: the payload's sign is "+ = good"
  for the subject, so red is right there. No local snapshot has a below-par `player_bars` row; that path is covered
  by the every-kind test only.
- **over_strips** at zoom 1.3 (`KIND_ZOOM`). M3c stills 8-24s: `motion_build/kinds_f2/contact.png`.
- **Purity:** fades and fills (`reveal`, `grow`) are snapped to steps of 1/64: twin_cloud's mid-fade differences are
  gone. boundary_zones' 16.6s frame (235px at up to 8 levels along the wedges' shared edges) is listed in that strip
  spec's `checkAllow` ({t, px, max, reason}; the recorder reports it as allowed with its reason, nothing else is
  loosened); in the latest runs it was identical anyway.
- **Drift:** every card visual and the still Reel-only kinds (team_best, pool_count) drift up 5 canvas px a second,
  in whole canvas pixels (`drift()`), on their own layer, so the content zone never holds still (M7). Sub-pixel drift
  broke `--check` (up to 21 levels); whole pixels pass. Latest checks: `motion_build/chk_n/`, all identical or
  1-level noise.

### M7: Reel checks in social_rules (18 Nov 2026)

- `src/components/ig/reel/frame.json`: the frame boxes, Instagram's keep-clear zones and the rule numbers, one source
  for the page (`motion.js` `FRAME`, `REEL_RULES`, `validateReel`) and Python.
- `services/social_rules.py`:
  - `reel_problems(spec)`: length 28-33s; first scene at 0, scenes in order, each on screen 1.2s or more (a
    must-read number); a lit item held 0.6s before the next; captions at most 5 words and 30 characters, and off in
    the closing scene; kicker and send line big enough on one line; the frame clear of Instagram's overlays; no ring
    on a below-par mark (rows, chips, players and grid cells "<row> · <column>"), except inside a both-sides decision
    (case_board, pick_one, keep_try).
  - `reel_captions(spec)`: the caption lines exactly as the page builds them.
  - `reel_still_problems(video)`: ffmpeg `freezedetect` on the content zone at -55dB for 0.8s. Calibrated on the
    round-2 video recorded before the drift: it flags the ranked bars holding still between beats (14-28s) and passes
    the new recording.
- `scripts/check_ig_reel.py reel.json [--video out.mp4]`: prints the problems, exits 1 if any.
- `tests/test_social_rules_reel.py` (11, including synthetic still and moving videos).
- Results: the round-2 spec and video and the MI fixture and video pass every check.
  Videos: `motion_build/r2_video2/smat_round2_react.mp4` (with the posted voice), `motion_build/mi_video/mi_retention_silent.mp4`.
- Not checked yet: "the same digits not on screen twice", and the voice's rate (M4).

### Round 9 (18 Nov 2026): drift fixes, M4, M5, M6

- **Drift (reviewer):** the drift is now a slow bob, up 12 canvas px and back every 4s (whole pixels), so a long scene
  can't carry a visual into the kicker. `?nodrift=1` (recorder `--nodrift`) turns it off; record that way for the
  still check, so the bob can't hide a still picture. **Finding:** with the bob off, the round-2 Reel holds still
  0.8-2.1s at a time in its ranked-bars and pool scenes (14-26s): between spoken names nothing moves. MI's fixture
  likewise. The fix belongs in the scenes and the planner: more beats (one name about every 0.8s) or a motion that runs
  while a name is read. Open; the check now says so honestly.
- **Gitignore:** the repo ignores `*.json`; `frame.json` (needed by the page and by Python), the reel test payloads
  and the voice timing fixtures are now excepted in `.gitignore`. Without that they would not be committed.

### M4: voice timing (18 Nov 2026)

- `services/reel_timing.py`: `spoken_count` (digits and "point" each a word, signs, percent, not out), `budget_problems`
  (95 spoken words), `estimate` (a timing file at 3 spoken words a second, no voice), `time_voice` (line starts from
  the voiced lengths as ig_reel_v2.align; word starts from word timestamps matched by ig_reel_v2.word_times; the live
  call `transcribe_words` is whisper-1 behind a parameter, never called in tests), `word_at` (an anchor by index or
  text, searched from a time), `place` (every scene starts on its anchor word, every dict with an `anchor` inside a
  scene gets its `at`, chapters follow their scenes, duration = voice + 0.6s hold, `timing` attached for captions).
- Tests (`tests/test_reel_timing.py`, on the two finished Reels' timing files in `tests/fixtures/reel_timing/`):
  the anchored round-2 spec placed from its own timing reproduces the hand-cut Reel's every scene start and end,
  beat, badge, card and send time and the duration to the millisecond, and passes `reel_problems`; both posted scripts
  fit the budget; a fake transcription and a failing one.

### M5: the planner (18 Nov 2026)

- `services/reel_plan.py`: `lit_keys` (highlighted rows, cases, a grid's best cell, gap rows), `card_scene` (the card's
  own visual, its scope, a beat on each lit item the line names, on that word; a below-par item is never lit except in
  a both-sides decision; case_board gets pages), `hero_scene` (the hook card's highlighted row at full size, the next
  row entering on its name), `close_scene` (the pick-one with captions off and the credit), `plan` (one scene a line:
  hook, cards, close; chapters). Kicker: the card's kicker, else its metric label.
- Tests (`tests/test_reel_plan.py`): lit keys, no below-par lit item, beats on the spoken word, the hero, and a planned
  Reel timed by `estimate` passing the Reel checks.
- Not done: a retention preset in `articles/ipl-retention/post.py` writing the scene list and script (the fixture
  script `make_reel_fixture.py` does it by hand for MI).

### M6: the pipeline swap (18 Nov 2026)

- `services/ig_reel_v2.py`: `make(..., motion=None)`; with `REEL_MOTION=1` (or `motion=True`) and a script with its
  closing pick-one (`plan["close"]`: line, question, lit, send, options?), `make_motion` voices the lines (hook, one
  per beat, close) with the same `voice_lines`, times them (`reel_timing.time_voice`), plans and places the spec, checks
  it (`reel_problems` + the budget; a failing spec raises), and records it with `record_motion` (`scripts/record_ig_reel.mjs`
  against `base`/ig/reel, voice muxed). Any failure falls back to the v2 path; the store step is shared (`_store`).
  Default off: today's Reels are unchanged.
- Tests (`tests/test_reel_motion.py`, voice, timestamps and recorder faked): one scene a line; voiced, timed, checked
  and recorded; a too-long spec isn't recorded; make falls back to v2 when motion fails.
- Dry run end to end (fake voice: the posted round-2 audio and fixed lengths; real Reel page on :3100; no paid call):
  29.6s, 888 frames; stills `motion_build/m6_dry/stills/contact.png`; `--check` identical.
- Not done: the script writer doesn't yet write `close` (the v2 prompt would need a close line, question and send line),
  so in production the motion path stays off until it does; `base` must be a site with the Reel page deployed; cover
  and Short from the motion frames (M6's last part) still come from the v2 helpers.

### Round 10 (18 Nov 2026): the still finding, the close, the retention preset, review fixes

- **Motion while a name is read (the still finding):** a lit item's ring breathes out and back once a second while
  it's held (`ringPulse`, `ringOn`; the scatter ring, the Reel-only lime ring and the fallback ring too); the pool
  count and its card bob while they're read; a squad board deals its chips across the time until the voice reaches
  the first name (`place` sets its stagger). No beats were added that the voice doesn't say. With the bob (drift) off:
  the round-2 Reel's stills went from six (0.8-2.1s) to one 0.8s stretch (21.6s, before the bob on the pool count was
  added); the retention preset's MI Reel passes the still check (`motion_build/ret3/`).
- **Dwell in `place`:** a ring waits 0.6s after the one before (names said in a quick list), or is dropped if it
  can't light before the scene ends; the check allows rounding (1 ms).
- **Captions:** one line also breaks before a word that would pass 30 characters (page and Python alike), and a
  one-word orphan only joins the line before when that still fits.
- **The closing line (M6):** `motion_close(script, close, team)` builds the pick-one from the legacy `--close`
  string, a dict, or the last line's own question, when it offers two short choices ("keep or release?",
  "Kohli or Rohit?"); the question moves off the last line onto the closing line with the send line, so it's said
  once; anything else means no motion Reel (v2). With motion on, `make` asks the script writer for a two-choice close
  (`script(close=PICK_ONE)`: a prompt line, no new call). **Motion stays default-off until the reviewer passes it.**
- **Review round 9 fixes (M6):** a late motion failure (after the voice) raises `MotionFailed` carrying the voiced
  lines, lengths and audio; v2 (`_make_v2`) reuses them instead of voicing again (the close rides on the last beat);
  the budget is checked before the voice; a partial mp4 at `out` is deleted on fallback and when v2 fails too;
  `time_voice` re-raises authentication and permission errors (401/403); the closing pick-one is built from a string
  or the script. The transcriber and recorder defaults are looked up at call time, so tests' fakes are always used.
  (Found while testing: a test with a bound default reached a real recorder against the live site page, a read-only
  page load that failed; no paid call was made because the fake audio failed ffmpeg first. Fixed by the call-time
  lookup.)
- **M5 retention preset:** `reel_plan.retention(slides, team, place)` writes the one-line-per-scene script from the
  cards' own numbers (names as tweets say them: Arshdeep, Rohit, Suryakumar) and the scene list: hero, squad board
  (the others named, best first, the ring on each), batting leader, bowling grid's best cell, the three calls (one
  page each), the biggest gap and who's available (one page), keep-or-release. MI 95 spoken words (at the budget),
  CSK 88, RCB 93; all pass the Reel checks timed by `estimate`.
- Tests: `tests/test_reel_motion.py` (10), `tests/test_reel_plan.py` (7), all Python reel tests 78 pass.

### Round 11 (18 Nov 2026): review round 10, M8, the final pass

- **Retention preset (review):** names are resolved to the full spoken name from the cards (`_say`: the carried rows
  and the cases; same initial and surname), then `called`: never a bare initial (CSK "Urvil", GT "Rashid"); with no
  full name, the surname. Phases said in words ("in the powerplay", "in the middle overs", "at the death"). Wins with
  two decimals ("Gill, 1.00"). The hook opens on the best Indian player when one added at least half the leader's wins
  (`overseas=` names the overseas players; the caller passes them from the squad); a section with nothing above par
  is left out (no batting leader, no positive bowling cell). Lit items anchor on the word the voice says.
  All ten teams (local slides.json, overseas from the local `auction_lots`, timed by `estimate`): CSK 88, MI 95,
  RCB 94, KKR 92, DC 82, LSG 83, SRH 84, RR 80, PBKS 85, GT 86 spoken words; no initials; every Reel check passes
  except RR's estimated length (27.9s, under 28: the voice decides the real length; a shorter script may need the
  template line).
- **Tests can't reach a paid or live call:** an autouse fixture in `tests/conftest.py` makes `record_motion`,
  `record`, `_client` (which `voice_lines` goes through) and `transcribe_words` raise unless a test fakes them.
- **M8, the SMAT round-up (`reel_plan.smat_round`):** the round's hero card counting up on frame 0 (with "That is 62
  runs more..." and the badge), then one franchise per beat in its own colour, the glow, stripe and its chapter
  segment changing with it (chapters may carry `team`: `ReelFrame` colours the segment), the no-IPL pool count with
  its best card, bid or pass. Four sides (the hero's and the next three); the rest are in the deck. Card lines become
  count-ups and spoken lines ("135* off 48" -> 135, "*", "off 48 balls"; "135 not out, off 48 balls"; "4/12 in 3"
  -> "four for 12"). On the round-2 data (`tests/fixtures/reel_timing/smat_round2_round.json`): 92 spoken words,
  32.0s estimated, every check passes, `--check` identical, the still check (bob off) passes. Stills:
  scratchpad `motion_build/m8/contact.png`. The SMAT builder itself (SMAT_ROUNDUP_PLAN R1-R6) isn't in this repo yet:
  `smat_round` takes the round's numbers as a dict, which that builder will produce.
- **Round 2's last still stretch:** gone with the pool count's bob: the round-2 Reel passes the still check with the
  bob off (`motion_build/r2_nd2/`).
- **Final pass:** Python: the full suite, 701 passed, 17 skipped (run with `DATABASE_URL` unset, so `database.py`
  loaded `.env`'s production URL; the tests mock the database, but next time export the local URL first, as
  CLAUDE.md says). JS: 144 pass; `App.test.js` and `FantasyPlanner.test.jsx` fail on HEAD too. Build passes.

### Round 12 (18 Nov 2026, after PR #330): motion length, the retention command, the first live motion Reel

- **The problem:** a live `REEL_MOTION=1 scripts/make_reel_v2.py --key ig:retention-mi-2027 --close "Keep or release?"`
  fell back to v2: the script, written to v2's short length, voiced at 25.7s (motion needs 28-33s).
- **Motion length (`services/ig_reel_v2.py`):** with motion on and length "short", `make` asks the writer for
  `LENGTHS["motion"]`: 70-78 spoken words of script (`reel_timing.spoken_count`, "1.98" is four), so 76-84 with the
  close's send line. The prompt explains spoken counting; `guard(..., spoken_range=)` rejects a script outside it
  ("N spoken words (too short ...)"), which the retry feeds back. Motion off: v2's lengths and prompt unchanged.
  The close: `--close` or the writer's two-choice question, as before (motion_close).
- **The voice's real rate is 2.65-2.95 spoken words a second**, slower than the 3.0 the estimate uses (numbers and
  lists are slow): MI's takes ran 95 words in 33.1s of voice, 89 in 32.4s, 84 in 31.9s. `reel_timing.BUDGET` (95) and
  `RATE` (3.0) are unchanged (the M8 SMAT estimate tests rely on them), but a 95-word script will usually run past
  33s: **the budget should be about 86** (open).
- **`close_hold`:** the pick-one holds up to 2.5s (not 0.6s) when the voice is a touch short, so the Reel reaches 28s.
- **`voice_and_record(spec, lines, ...)`:** make_motion's voice -> time -> place -> check -> record, shared by presets;
  `record_motion(..., nodrift=)`. A late failure keeps the voice, timing and placed spec on `MotionFailed.voiced`.
- **Retention command:** `REEL_MOTION=1 scripts/make_reel_v2.py --preset retention --team MI --out mi.mp4
  [--nodrift] [--keep dir] [--slides f] [--retained csv] [--base URL]`: slides from the pack's carousel
  (ig:retention-<team>-2027, read only), else `articles/ipl-retention/<team>/slides.json`; `overseas` from
  `data/auction_raw/ipl/2027/retained_official.csv` (`ig_reel_v2.overseas_of`); `make_retention` plans
  (reel_plan.retention), voices, times, places and records. Preview only: `--store` is refused. `--keep` saves
  reel.json + voice.mp3 (also on failure) to re-record or check with no new paid call.
- **Preset script leaner:** "Only 3 others passed a quarter of a win: ...", "Three calls: Rohit at 16.3 crore, then
  Chahar and Rickelton." (the three prices took the voice 7.1s), "Biggest gap: middle-overs spin. ...". MI: 84 spoken
  words (was 95).
- **Live run (owner-approved paid calls, 3 runs, base https://hindsightcricket.com, no store, no DB writes):**
  run 1 (95 words) 33.7s, run 2 (89 words) 33.0s (the hold tipped it over): both refused by the length check
  before recording. Run 3 (84 words): **32.5s**, 977 frames, recorded `--nodrift`; `scripts/check_ig_reel.py
  reel.json --video` -> no problems (exit 0). The posting version (with the bob) re-recorded from the kept spec
  and voice. Scratchpad `motion_live/`: `mi_retention_nodrift.mp4`, `mi_retention.mp4`, `check_output.txt`,
  `run3/reel.json`, `run3/voice.mp3`, `stills/contact.png`.
- **Seen in the stills (owner to look at):** the posted MI carousel (wdAzQNlIm) predates change B, so its bowling grid
  is the old six (Bumrah, Arshdeep, Santner, Boult, Chahar, Thakur); the squad board is shown small with empty space
  below before the push; 32.5s is near the 33s cap.
- Tests: `tests/test_reel_motion.py` (+8: writer length with a faked model, motion off unchanged, close hold,
  overseas csv, preset voiced/placed/recorded, keeps voice on failure, the command is preview only), full Python suite
  723 pass; reel JS tests 74 pass; build passes.

### Round 12b (18 Nov 2026, review of PR #331; no paid calls)

- **Estimate at the voice's rate:** `reel_timing.RATE` 2.8 (was 3.0), `BUDGET` 86 (was 95): 86 words at 2.8 with 7
  lines' gaps and the hold is 31.8s. Word ranges agree everywhere: the motion Reel is `ig_reel_v2.MOTION_WORDS`
  76-86 spoken words with its close (top = BUDGET), the script 70-80 plus the 6-word send line; the help text says so.
  The posted round-2 Reel (91 words, voiced at 2.96/s) is now over the budget, which the timing test states.
- **SMAT round-up shorter:** "That is 62 runs above par: the most by an IPL player." (was "...runs more than an
  average player from the same spots: ..."): 83 spoken words, was 92.
- **Hero unit:** `reel_plan.metric_unit` puts the metric's unit after the hero numbers ("+1.98 WINS"), from
  `metric.unit` or the label's first word (wins, runs, wickets, impact).
- **gap_fits:** the header row wraps ("now · playoff" under the label) when narrower than the card; it was cut at the
  right edge in the Reel ("...playo"). On the carousel card nothing changes unless the row doesn't fit.
- **Squad board:** `KIND_ZOOM.squad_board` 1.15: laid out narrower, it fills the box before the push (1.3 ran past
  the box's bottom for MI). While pushed, chips on other rows can still run off the right edge (as before).
- **Data in git:** `.gitignore` excepts `data/auction_raw/ipl/2027/retained_official.csv` and `released_derived.csv`;
  both committed, so the preset works on a clean checkout.
- **Preset slides:** `--slides`, else the local `articles/ipl-retention/<team>/slides.json`, else the queued pack
  (a SELECT that reads PRODUCTION when DATABASE_URL is unset; the help says so).
- **MI re-recorded free:** re-planned with this code on run 3's saved word timing and voice (same lines), on a local
  :3100 page: `motion_live/mi_retention_v2.mp4` and `mi_retention_v2_nodrift.mp4` (32.5s); `check_output_v2.txt`:
  no problems. Stills: `motion_live/stills_v2/contact.png` (hero "+1.98 WINS", gap line whole, board filling the box).
- Tests: Python 724 pass; JS reel, story and charts 84 pass; build passes.

## Merge checklist

1. **Commit everything listed by `git status`**, including the new JSON files `.gitignore` now lets through
   (`src/components/ig/reel/frame.json`, `src/components/ig/reel/__fixtures__/*.json`, `tests/fixtures/reel_timing/*.json`):
   the page imports `frame.json`, and the build and Python checks need it.
2. **Regression goldens:** change B changes the squad view's bowling grid (the five who bowl most per match, by
   matches played, at least a third of the side's games). Re-run `python scripts/regression_snapshot.py check` against
   a restarted local API after merge and re-baseline any golden that covers the team page's squad group
   (`/team-squad`). Not run in this work (it would hit the main checkout's :8000).
3. **Retention slides:** rebuild with `articles/ipl-retention/post.py` to see the new bowling grids (five rows) and
   red below-par bars; the posted carousels are unchanged until rebuilt.
4. **Carousel colours (change A):** below-par bars in `metric_bars`, `deep_compare` and `player_bars` are red on every
   card from the next render (3 of 26 local slides changed, only those bars). Expect the same on the next carousels.
5. **REEL_MOTION switch criteria** (it stays off): (a) the reviewer passes M6; (b) the Reel page is deployed (the
   recorder opens `<SITE>/ig/reel`); (c) one motion Reel made end to end with the real voice and word timestamps,
   checked by `scripts/check_ig_reel.py --video` on a `--nodrift` recording, and watched on a phone with the guides;
   (d) the v2 fallback seen once (e.g. a bad base URL) to confirm a post still gets its Reel; then set `REEL_MOTION=1`.
6. **No secrets or prod data in the diff:** fixtures are posted cards' numbers and the two posted Reels' timing files.

## Owner questions

1. Caption lit word: gold (plan), lime (round-2 Reel) or the team colour (Dhoni Reel)? Gold is in.
2. Sankey cards: "Lost the toss" sits on its node bar and "Tied or no result" over the ribbons, on the card itself:
   fix the card?
3. Red below par now also lands on single named players on cards (e.g. Axar Patel −28.4 on a Tilak post): fine under
   the no-blame rule, or limit red to team or role rows?
4. The retention hook prefers an Indian player when one added half the leader's wins (CSK opens on Mhatre 0.41 over
   Hosein 0.44): right threshold?
5. Motion Reels keep a slow 12px bob on card visuals so the picture is never fully still; the still check runs with
   it off. Keep the bob, or rely on the rings and count-ups alone?

## Status (worktree copy of MOTION_REEL_PLAN.md's tracker; the main checkout's file is not edited)

| # | Chunk | Status |
|---|---|---|
| M1 | Reel page + frame + recorder + safe-area check | [x] 17 Nov (uncommitted) |
| M2a | Primitives, motion prop, fallback, every-kind test | [x] 17 Nov (uncommitted) |
| M2b | Ranked bars, side by side, scorecards, tiles, round-2 kinds | [x] 17 Nov (uncommitted; `recent_results` plays the fallback) |
| M3a | Boards and heat grids | [x] 17 Nov (uncommitted) |
| M3b | Lines over time and scatter | [x] 17 Nov (uncommitted; voice-timed marker pops not done) |
| M3c | Field and pitch, flows, auction | [x] 18 Nov (uncommitted; innings_wagon plays the fallback) |
| M7 | Checks in social_rules | [x] 18 Nov (uncommitted) |
| M4 | Voice timing | [x] 18 Nov (uncommitted; tested on the posted timing files, no paid calls) |
| M5 | Planner | [x] 18 Nov (uncommitted; services/reel_plan.py with the retention preset) |
| M6 | Pipeline swap | [~] 18 Nov: make(motion=True), the close line, review fixes; default off until review passes; cover/Short from motion frames not done |
| M8 | SMAT round-up | [x] 18 Nov (uncommitted; reel_plan.smat_round; the SMAT builder that feeds it is SMAT_ROUNDUP_PLAN R1-R6) |

## Verification (latest)

- Tests: `CI=true npx react-scripts test --watchAll=false src/components/ig/reel src/components/story src/components/charts`: 84 pass, 12 todo. Python: `pytest tests/test_reel_plan.py tests/test_reel_motion.py tests/test_reel_timing.py tests/test_reel_v2.py tests/test_social_rules_reel.py tests/test_squad_view_attack.py tests/test_social_rules.py tests/test_audit_social_rules.py tests/test_squad_review.py tests/test_ipl_squads.py` (82 pass; the full suite 701 pass). Full JS suite: 144 pass; App.test.js and FantasyPlanner.test.jsx fail on HEAD too (not this work).
- Build passes (warnings only from a node_modules source map).
- Stills: `motion_build/m1_stills6/` (MI push), `motion_build/kinds_a..e/contact.png` (kind strips), `motion_build/r2_stills2/` (round 2, guides).
- `--check`: `motion_build/chk_k_results.txt` (7 specs, 2 runs: no real difference).
- Carousel before/after: `motion_build/slides2/` (26 slides byte-identical).
- Earlier video: `motion_build/r2_video/smat_round2_react.mp4` (31.4s, 56s to record).

## Open issues / next

- **Owner questions:** (1) and (2) answered 18 Nov: below par red on the cards too (change A), the carousel grid is
  the regular attack (change B). Open: (3) caption lit word: gold (plan), lime (round-2 Reel) or the team colour
  (Dhoni Reel)? (4) sankey's card labels overlap its node bars and ribbons: fix the card?
- **Before merge:** re-baseline the regression goldens if they cover the squad group; rebuild the retention slides.
- Fixture data: the MI Reel grid came from two read-only production queries (`motion_build/mi_attack_query.json`)
  because the local slides.json predates change B; rebuilt slides carry the regular attack themselves.
- Planner (M5) must set: beats (`key` = the name a kind marks; fallback kinds need a `box`), `pages` for long boards,
  `push` for boards, `plan.case_every`, and the kicker/send-line lengths `validateReel` checks.
- 12 kinds have no test payload (test todo list). Recharts/echarts site-only kinds may animate on their own.
- Next: cover and Short from the motion frames (M6); REEL_MOTION on per the merge checklist; wire `reel_plan.retention`
  into `articles/ipl-retention/post.py` and `smat_round` into the SMAT builder.
- To resume: all work is uncommitted in this worktree; scratch files are under the session scratchpad `motion_build/`.
  Symlink node_modules from the main checkout, `BROWSER=none PORT=3100 REACT_APP_API_URL=http://localhost:8000
  npx react-scripts start`, then `node scripts/record_ig_reel.mjs --spec src/components/ig/reel/__fixtures__/smat_round2.reel.json
  --base http://localhost:3100 --out <dir> --stills 0,1.5,5,13.5,21.5,28 --check`.

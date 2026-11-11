# The living India XI

A permanent page that shows India's XI spot by spot, with the case for and against each player, refreshed after every
India match. Agreed with the user, 10 Nov 2026. Selection is the argument that never ends; this is the page people can
point to. No-blame applies throughout: the page weighs evidence for a spot, it never says who failed.

## What it is

`/team?team=India` gets an **XI** group (T20I first, ODI second, a switch):

- **The XI as it stands:** eleven slots by role (openers, 3–4, 5–7, pace in the powerplay, spin in the middle overs,
  pace at the death; the keeper marked). Each slot shows the incumbent (who played it in the recent XIs) with one
  number.
- **Tap a slot: the case.** For the incumbent and up to three contenders: the number for and the number against
  each, on the same measures, with sample sizes; small samples flagged. Contenders come from data, not opinion.
- **What moved.** After each match, a short dated log: "Tilak Varma: 3 → 4 in the last two XIs", "Arshdeep's death
  economy 8.9 → 8.4 over his last 10". This is also the morning-after post (PITCH_BRIEF_PLAN.md).
- **Against the template.** India's XI graded on the same role measures as playoff sides, against the top-10
  international sides (not the IPL template).

## Design decisions to make with the user (I0)

1. **Who is a contender?** Proposal: anyone with India caps in the format in the last 24 months, plus the top few by
   role in the IPL and domestic T20s on the measures that repeat (strike rate, economy, dot %, control %), not wins
   added.
2. **Which measures per slot?** The winners' template's (average and strike rate for batting slots; wickets per four
   overs and economy for bowling slots), plus one "why" picture per player from his profile cards.
3. **Wording.** "The case for / the case against", never "should be dropped". Verdicts are on the spot ("contested",
   "settled"), by how close the contenders are.

## Chunks

| # | Chunk | Output |
|---|---|---|
| I0 | Sign off the three decisions above on a mockup (one slot, real numbers). | mockup, decisions recorded here |
| I1 | **Slots from recent XIs.** India's last N matches per format: who filled each role (batting position, overs by phase), from the ball-by-ball data; the incumbent per slot; handles rested players and a changing XI. | `services/india_xi.py`, tests against known XIs |
| I2 | **Contenders and cases.** The pool per slot; each player's numbers for the slot's measures in internationals and in the IPL separately; the for/against lines (reuse the retention posts' `case()`); small-sample flags. | service + tests |
| I3 | **International template.** The role benchmarks from top-10 sides' winning XIs, the way the IPL template was built (season ledger → roles → percentiles); only measures stable across years kept. | `services/pinned/team_template_T20I.json` |
| I4 | **Endpoint and page.** `GET /team-xi?team=India&format=`; the XI card, the slot sheet, the "what moved" log; profile rules; phone screenshots. | route, `TeamPage.jsx` |
| I5 | **Refresh and post.** Recompute after each India match in the nightly run; the diff becomes the "what moved" entries and a pitch for the morning brief. | nightly step |
| I6 | **ODI variant**; then other top sides if it earns its keep. | |

## Risks

- Positions shuffle in T20Is, so "the incumbent at 5" can be noisy: use the last 5–8 XIs and show the share.
- Contender numbers from the IPL aren't international numbers: show them side by side, labelled, not blended.
- Selection opinions attract heat: the wording rule (decision 3) is part of the definition of done.

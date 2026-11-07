# Suggested fields: coverage circles from where a batter hits it

The broadcast idea, from our data: given where a batter hits the ball (by phase and bowler type), place nine fielders
within the fielding restrictions, each with a realistic coverage area, so the field covers as much of his scoring as it
can. For a batter ("how to set a field to him"), or a bowler ("the field for him against right- or left-handers").
Proposed to the user, 7 Nov 2026; they said go.

## Why a model, and not "the fielder who matters"

We don't know where the fielders stood. Where a batter's boundaries go partly records the fields set to him (a gap left
open gets hit), and catches can only happen where a fielder is (the bullet-holes problem: #276 removed the "fielder who
matters" line for this reason). A model of the field built from where he hits the ball is the honest version.

## The inputs

- **Direction, not distance.** Each ball's angle from the batter (`wagon_x`, `wagon_y`, a fixed view of the ground) is
  much less shaped by the field than where the ball stopped. A single's coordinates are where a fielder stopped it, which
  is the field again.
- **Distance class from the outcome, not the coordinate:**
  - **Boundary:** a 4 or a 6, which needs the rope covered.
  - **Ground ball in the ring:** 0–2 runs, along the ground.
  - **In the air:** caught, or a mistimed shot, with control 0 where it's tagged.
- **Weights:** runs and wickets. A field that saves boundaries but gives easy singles is worse at the death than in
  the middle overs.
- **Cuts:** phase × bowler kind (or type), × batter's hand for a bowler's field. Same filters as the wheel's gear
  (#276).
- **Coverage:** about 45–55% of balls have a position. Each field says how many balls it was built from.

## The model

- **Positions:** a polar grid of candidates.
  - **Inner ring:** about 15–30 m out (scaled to the grid's 181-unit boundary).
  - **Boundary:** riders on the rope.
- **Reach:** each candidate covers an area.
  - **An inner fielder:** a circle (radius R_in) for ground balls.
  - **A boundary rider:** an arc along the rope (half-width A_out) for boundaries and catches.
  - R_in and A_out are assumptions: we have no ball speed or fielder data. The page shows them as such and draws the
    circles, which is the broadcast look.
- **Constraints:**
  - Nine fielders, plus the keeper and bowler (fixed).
  - **Outside the circle:** at most 2 in the powerplay and 5 after (IPL/T20I rules; the ODI rules differ by
    powerplay).
  - A minimum spacing.
- **Objective:** maximise the weighted share of his balls covered, with runs and wickets weighted by phase. Solved by
  greedy placement plus local search; nine fielders is small enough to search well.
- **Output:**
  - The nine positions with their circles and arcs.
  - The share of his runs the field covers, and the gaps left (the biggest uncovered arc).
  - For comparison, a standard field for the phase scored the same way, so the suggestion has a baseline.

## Chunks

| # | Chunk | Output |
|---|---|---|
| F0 | **Data check.** How angle and outcome look for a few batters; how much changes by phase and bowler type; whether angle alone separates players (Rohit, Livingstone, Pooran, Kohli). | A notebook-style script and a findings note |
| F1 | **The field solver.** Candidates, reach, rules, objective; a standard-field baseline. Unit tests: the rules are never broken, and a batter who only hits square gets a square field. | `services/field_model.py` |
| F2 | **Prototype.** Rohit and Livingstone, by phase × pace/spin. Their suggested fields, as post cards and on a mockup card, to the user for a sense check (does it look like a field a captain would set?). | Cards; the user decides if it ships |
| F3 | **Profile card.** "A field for him" in the batter's scouting group, phase and bowling from the wheel's gear; a bowler's version against right- and left-handers. Revamp rules: one picture, one-line note naming the cut and "a model, not his actual fields". | A profile card |
| F4 | **Posts.** A scouting-post card ("the field for Livingstone at the death"). | `articles/scouting` |

## Open questions for the user at F2

- Should the reach be the same for everyone, or vary by fielder? Same for everyone: we don't model fielders.
- Should runs and wickets be weighted per phase (death: save runs; middle: take wickets), or one weight?
- Should the field show the keeper and slips explicitly when the model puts a fielder behind the wicket?

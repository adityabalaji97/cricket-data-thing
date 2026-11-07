# Field coverage: F0 findings (7 Nov 2026)

`scripts/analysis/field_f0.py`, all men's T20s since 2023. The four batters: Rohit Sharma, Liam Livingstone, Nicholas
Pooran (mirrored to a batter's view) and Virat Kohli.

## 1. Coverage

76–91% of these batters' balls carry a position: Rohit 86%, Livingstone 76%, Pooran 86%, Kohli 91% (1.2k–4.2k balls
each). This is better than the ~50% for catches alone.

## 2. Distance records the field, as suspected

Median distance (1 = the rope):

| | Boundaries | Runs 1–3 | Caught |
|---|---|---|---|
| All four | ~1.0 | 0.75–0.77 | 0.40–0.75 |

Balls that ran stop about three-quarters of the way out, which is where fielders cut them off. So the model uses
**direction** (angle) plus the **outcome class** (boundary, ran, in the air), not distance.

## 3–4. Direction separates few batters from the average

JS distance between run-share profiles, 12 sectors of 30°:

| | Rohit | Livingstone | Pooran | Kohli |
|---|---|---|---|---|
| Noise floor (random halves of his own balls) | 0.12 | 0.10 | 0.08 | 0.09 |
| v the average batter of his hand | **0.19** | 0.08 | 0.05 | 0.09 |
| Himself, 2023–24 v 2025–26 | 0.20 | 0.07 | 0.10 | 0.13 |

- **Only Rohit is clearly distinct:** 18% of his runs go backward of square on the leg side (the pull). He has also
  changed most since 2023.
- **Livingstone, Pooran and Kohli are within noise of the average batter**, at this resolution and across all their
  balls. A personal field for them would mostly be the standard one.

## 5. The cuts move further, but thin out

Phase × pace/spin moves a profile 0.07–0.37 from his overall one, and 0.08–0.39 from the average batter in the same
cut. But the noise grows as the sample shrinks (about 0.2 at 250 balls), and some cuts are tiny: Rohit's death pace is
44 balls; Kohli's death spin 34.

## What this means for F1 (the solver)

1. **Shrink to the standard field.** A batter's profile in a cut = his counts plus a prior of k balls drawn from the
   average batter of his hand in that cut (k about 200, to be tuned against the noise floor). A thin cut becomes the
   standard field; a deep, distinctive one (Rohit v powerplay pace, 512 balls) moves away from it.
2. **Only claim a difference that beats noise.** The card shows "a standard field fits him" when his shrunk profile
   is within the noise floor of average, and highlights only the fielders that moved for him otherwise.
3. **Minimum balls per cut:** 150 to show a field at all. Below that, "too few balls"; the wheel filter does the same.
4. **The baseline is the average batter of the same hand in the same cut**, from delivery_details (computed in SQL;
   fast). That's both the standard field and the comparison.
5. **Expect most suggestions to be small tweaks:** one or two fielders moved from standard. Present it that way: "the
   field for him: standard, but square leg back for the pull", not a dramatic reset.

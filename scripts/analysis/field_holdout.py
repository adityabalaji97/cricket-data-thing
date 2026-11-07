import logging, sys, json, math
sys.path.insert(0, '/Users/adityabalaji/cdt/cricket-data-thing'); sys.path.insert(0, '/Users/adityabalaji/cdt/cricket-data-thing/articles/fields')
logging.disable(logging.INFO)
from datetime import date
import prototype as P
from services import field_model as F
from database import get_session
db = next(get_session())
avg = P.average_profiles(db, '2023-01-01')
orig = P.date
cases = [c for c in P.CASES if c != ("Rohit Sharma", "death", "pace bowler")] + [("Nicholas Pooran", "middle", "spin bowler"), ("Virat Kohli", "powerplay", "pace bowler"), ("Nicholas Pooran", "death", "pace bowler"), ("Virat Kohli", "middle", "spin bowler")]
data = []
for name, phase, kind in cases:
    class D(date):
        @classmethod
        def today(cls): return date(2024, 12, 31)
    P.date = D
    hand, fit = P.player_profile(db, name, phase, kind, '2023-01-01')
    P.date = orig
    _, test = P.player_profile(db, name, phase, kind, '2025-01-01')
    data.append((name, phase, kind, hand, fit, test))

def smooth(p, sd_deg):
    if not sd_deg: return p
    w = [math.exp(-0.5 * ((d * F.BIN) / sd_deg) ** 2) for d in range(-6, 7)]
    s = sum(w); w = [x / s for x in w]
    return {k: [sum(v[(i + d) % F.NBINS] * w[d + 6] for d in range(-6, 7)) for i in range(F.NBINS)] for k, v in p.items()}

for k in (200, 600, 1500):
    for sd in (0, 10, 20):
        gains = []
        for name, phase, kind, hand, fit, test in data:
            a = avg[(hand, phase, kind)]
            his = F.solve(F.shrink(smooth(fit, sd), a, k), phase); std = F.solve(a, phase)
            vals = F.ball_values(test, phase); tot = sum(x + y for x, y in vals) or 1
            gains.append((F.field_value(his, vals) - F.field_value(std, vals)) / tot)
        print(f"k={k} smooth={sd}: mean gain {sum(gains)/len(gains):+.3f}, beats standard in {sum(g > 0.005 for g in gains)}/{len(gains)}, worst {min(gains):+.3f}, best {max(gains):+.3f}")
# How good is the standard field itself out of sample, against "his own field fitted on his test balls" (the ceiling)?

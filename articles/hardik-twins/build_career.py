"""One-off: career vectors 2015 to today (strong sides), both roles, pickled for the Hardik post's twins.
Careers since 2015 aren't in player_vectors (the profile's window is since 2024), and this post covers his whole IPL."""
import os, pickle, sys, time
from datetime import date
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from database import get_session
from services.twins_features import build_period
db = next(get_session())
out = {}
for role in ("bat", "bowl"):
    t = time.time()
    vectors, qual = build_period(db, role, date(2015, 1, 1), date.today(), unit="window")
    out[role] = vectors
    print(role, len(vectors), "players,", len(qual["players"]), "qualified,", f"{time.time()-t:.0f}s", flush=True)
pickle.dump(out, open(HERE / "career_vectors.pkl", "wb"))
print("saved")

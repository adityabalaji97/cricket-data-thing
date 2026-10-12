"""
How the Reel voice (services/ig_reel_v2.py) says names. "say" replaces the name in what the voice reads only (captions
keep the real spelling); "hint" goes into the voice's instructions when the name is in the script. Add a name when a
Reel gets it wrong.
"""
PRONOUNCE = {
    "Bumrah": {"say": "Boomrah"},  # BOOM-rah, a short "oo" (picked by ear, 12 Oct 2026)
}

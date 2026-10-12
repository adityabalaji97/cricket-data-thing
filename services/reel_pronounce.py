"""
How the Reel voice (services/ig_reel_v2.py) says names. "say" replaces the name in what the voice reads only (captions
keep the real spelling); "hint" goes into the voice's instructions when the name is in the script. Add a name when a
Reel gets it wrong.
"""
PRONOUNCE = {
    "Bumrah": {"say": "Bumrah",
               "hint": "Pronounce Bumrah as BOOM-rah with a short, clipped 'oo' (as in 'book'), stress on the first syllable."},
}

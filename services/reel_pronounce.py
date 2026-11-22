"""
How the Reel voice (services/ig_reel_v2.py) says names. "say" replaces the name in what the voice reads only (captions
keep the real spelling); "hint" goes into the voice's instructions when the name is in the script. Add a name when a
Reel gets it wrong.
"""
PRONOUNCE = {
    "Bumrah": {"say": "Boomrah"},  # BOOM-rah, a short "oo" (picked by ear, 12 Oct 2026)
    "Raina": {"hint": "Raina is said RYE-nuh (rhymes with China)"},  # Rana v Raina in one line (Rana Reel, 20 Nov 2026)
    "Dhull": {"hint": "Dhull is said like the English word dull"},
    "lakh": {"hint": "lakh is said LAHK (rhymes with dock), the Indian unit of 100,000"},
    "Bhuvneshwar": {"hint": "Bhuvneshwar is said BHOOV-nesh-war"},
    "Rana": {"hint": "Rana is said RAA-nuh, a long first a, never like Raina"},
}

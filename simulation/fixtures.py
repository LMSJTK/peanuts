"""Sample validation fixtures for quick manual runs."""

from .pitch import BatterRatings, PitcherRatings, DefenseRatings

SAMPLE_PITCHER = {
    "name": "Cy Lumen",
    "ratings": PitcherRatings(control=60, velocity=65, deception=55),
}

SAMPLE_BATTER = {
    "name": "Ivy Sparks",
    "ratings": BatterRatings(contact=58, power=62, discipline=52),
}

SAMPLE_DEFENSE = DefenseRatings(range=55, surety=60)

SAMPLE_STADIUM = {
    "name": "Harbor Oddity Park",
    "modifiers": {
        "global": 0.02,  # Slight home edge
        "power": 0.05,  # Friendly breeze to the alleys
        "aggression": -0.01,
    },
}

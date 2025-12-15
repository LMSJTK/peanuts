"""Simulation utilities for Peanuts and Crackerjacks."""

from .pitch import resolve_pitch_outcome, PitchParticipants, PitchContext, PitchOutcome
from .state import HalfInningState, PitchEvent
from .fixtures import SAMPLE_PITCHER, SAMPLE_BATTER, SAMPLE_DEFENSE, SAMPLE_STADIUM

__all__ = [
    "resolve_pitch_outcome",
    "PitchParticipants",
    "PitchContext",
    "PitchOutcome",
    "HalfInningState",
    "PitchEvent",
    "SAMPLE_PITCHER",
    "SAMPLE_BATTER",
    "SAMPLE_DEFENSE",
    "SAMPLE_STADIUM",
]

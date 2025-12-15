"""Core pitch resolution utilities.

The functions in this module are pure with respect to input arguments and
return deterministic outputs whenever a seed is provided. All randomness is
provided by a local ``random.Random`` instance scoped to the call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import random


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class PitcherRatings:
    control: float
    velocity: float
    deception: float


@dataclass(frozen=True)
class BatterRatings:
    contact: float
    power: float
    discipline: float


@dataclass(frozen=True)
class DefenseRatings:
    range: float
    surety: float


@dataclass(frozen=True)
class PitchParticipants:
    pitcher: PitcherRatings
    batter: BatterRatings
    defense: DefenseRatings


@dataclass(frozen=True)
class PitchContext:
    balls: int
    strikes: int
    outs: int
    bases: tuple[bool, bool, bool]
    situational_modifiers: Dict[str, float]

    def combined_modifier(self, role: str) -> float:
        base = self.situational_modifiers.get(role, 0.0)
        shared = self.situational_modifiers.get("global", 0.0)
        return base + shared


@dataclass(frozen=True)
class PitchOutcome:
    result: str
    description: str
    in_zone: bool
    did_swing: bool
    contact_quality: float


def resolve_pitch_outcome(
    participants: PitchParticipants,
    context: PitchContext,
    seed: Optional[int] = None,
    rng: Optional[random.Random] = None,
) -> PitchOutcome:
    """Resolve a single pitch using player ratings and situational modifiers.

    The function is pure: given the same inputs and an explicit ``seed`` it will
    always produce the same ``PitchOutcome``. If an ``rng`` instance is passed in
    it will be used directly and the ``seed`` will be ignored, enabling callers
    to drive deterministic sequences across multiple pitches.
    """

    local_rng = rng or random.Random(seed)

    pitcher_advantage = (
        participants.pitcher.control * 0.35
        + participants.pitcher.velocity * 0.35
        + participants.pitcher.deception * 0.30
    )
    batter_pressure = (
        participants.batter.contact * 0.4
        + participants.batter.discipline * 0.35
        + participants.batter.power * 0.25
    )
    advantage_delta = pitcher_advantage - batter_pressure

    zone_modifier = context.combined_modifier("pitcher") - context.combined_modifier(
        "batter"
    )
    zone_probability = _clamp(
        0.55 + 0.003 * advantage_delta + 0.01 * (context.strikes - context.balls)
        + zone_modifier,
        0.25,
        0.9,
    )
    in_zone = local_rng.random() < zone_probability

    swing_bias = _clamp(
        0.5
        - 0.002 * (participants.batter.discipline - participants.pitcher.deception)
        + 0.05 * context.strikes
        + context.combined_modifier("aggression"),
        0.15,
        0.95,
    )
    swing_probability = swing_bias if not in_zone else _clamp(swing_bias + 0.08, 0.15, 0.99)
    did_swing = local_rng.random() < swing_probability

    if not did_swing:
        return PitchOutcome(
            result="called_strike" if in_zone else "ball",
            description="Called strike" if in_zone else "Ball out of zone",
            in_zone=in_zone,
            did_swing=did_swing,
            contact_quality=0.0,
        )

    # Swing decision made; determine contact quality.
    contact_base = (
        participants.batter.contact * 0.55
        + participants.batter.power * 0.25
        + participants.batter.discipline * 0.2
    )
    pitch_difficulty = (
        participants.pitcher.velocity * 0.4
        + participants.pitcher.deception * 0.4
        + participants.pitcher.control * 0.2
    )
    contact_quality = contact_base - pitch_difficulty
    contact_quality += context.combined_modifier("contact") * 100
    contact_quality += local_rng.uniform(-8.0, 8.0)

    if contact_quality < -5:
        return PitchOutcome(
            result="swinging_strike",
            description="Swing and a miss",
            in_zone=in_zone,
            did_swing=did_swing,
            contact_quality=contact_quality,
        )

    foul_wall = _clamp(0.25 + 0.002 * (2 - context.strikes), 0.1, 0.45)
    if local_rng.random() < foul_wall:
        return PitchOutcome(
            result="foul",
            description="Fouled away",
            in_zone=in_zone,
            did_swing=did_swing,
            contact_quality=contact_quality,
        )

    defensive_cushion = (
        participants.defense.range * 0.4 + participants.defense.surety * 0.6
    )
    in_play_score = contact_quality + context.combined_modifier("power") * 120
    in_play_score -= defensive_cushion * 0.2

    thresholds = (
        5,  # out
        30,  # single
        55,  # double
        75,  # triple
    )
    if in_play_score < thresholds[0]:
        result = "inplay_out"
        description = "Weak contact; fielded for an out"
    elif in_play_score < thresholds[1]:
        result = "single"
        description = "Grounder finds a hole"
    elif in_play_score < thresholds[2]:
        result = "double"
        description = "Line drive into the gap"
    elif in_play_score < thresholds[3]:
        result = "triple"
        description = "Driven to the corner"
    else:
        result = "homerun"
        description = "Crushed beyond the fence"

    return PitchOutcome(
        result=result,
        description=description,
        in_zone=in_zone,
        did_swing=did_swing,
        contact_quality=in_play_score,
    )

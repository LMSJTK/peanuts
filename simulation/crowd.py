"""Crowd energy accumulator and modifier helper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class CrowdEnergySnapshot:
    energy: float
    modifiers: Dict[str, float]


class CrowdEnergyAccumulator:
    """Track and decay crowd energy, exposing bounded simulation modifiers."""

    def __init__(
        self,
        base_energy: float = 15.0,
        max_energy: float = 100.0,
        decay_rate: float = 0.12,
        modifier_cap: float = 0.08,
    ) -> None:
        self.energy = base_energy
        self.max_energy = max_energy
        self.decay_rate = decay_rate
        self.modifier_cap = modifier_cap
        self._last_modifiers: Dict[str, float] = {}

    def tick(self) -> CrowdEnergySnapshot:
        """Apply decay and surface the latest modifiers."""
        decayed = self.energy * (1 - self.decay_rate)
        self.energy = _clamp(decayed, 0.0, self.max_energy)
        self._last_modifiers = self._build_modifiers()
        return CrowdEnergySnapshot(energy=self.energy, modifiers=self._last_modifiers)

    def apply_event(self, outcome: str, runs_scored: int, contact_quality: float) -> CrowdEnergySnapshot:
        """Adjust energy in response to a pitch outcome.

        Celebratory events add momentum while outs and weak contact bleed it off.
        """

        swing_bonus = 0.0
        scoring_bonus = runs_scored * 6.0

        if outcome in {"single", "double", "triple"}:
            swing_bonus = 6.0
        elif outcome == "homerun":
            swing_bonus = 12.0
        elif outcome == "walk":
            swing_bonus = 2.5
        elif outcome in {"called_strike", "swinging_strike", "strikeout", "inplay_out", "foul"}:
            swing_bonus = -2.5

        swing_bonus += contact_quality * 0.02

        self.energy = _clamp(self.energy + swing_bonus + scoring_bonus, 0.0, self.max_energy)
        self._last_modifiers = self._build_modifiers()
        return CrowdEnergySnapshot(energy=self.energy, modifiers=self._last_modifiers)

    def _build_modifiers(self) -> Dict[str, float]:
        momentum = self.energy / self.max_energy
        return {
            "global": self._bounded_modifier(0.04 * momentum),
            "contact": self._bounded_modifier(0.05 * momentum),
            "power": self._bounded_modifier(0.06 * momentum),
            "aggression": self._bounded_modifier(0.02 * momentum),
        }

    def _bounded_modifier(self, raw_value: float) -> float:
        return _clamp(raw_value, -self.modifier_cap, self.modifier_cap)

    def snapshot(self) -> CrowdEnergySnapshot:
        return CrowdEnergySnapshot(energy=self.energy, modifiers=self._last_modifiers or self._build_modifiers())

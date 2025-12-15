"""State containers for inning progression and pitch logging."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence
import random

from .crowd import CrowdEnergyAccumulator, CrowdEnergySnapshot
from .pitch import PitchContext, PitchOutcome, PitchParticipants, BatterRatings, PitcherRatings, DefenseRatings, resolve_pitch_outcome


@dataclass
class PitchEvent:
    number: int
    batter: str
    outcome: str
    detail: str
    balls_before: int
    strikes_before: int
    outs_before: int
    balls_after: int
    strikes_after: int
    outs_after: int
    bases_before: tuple[bool, bool, bool]
    bases_after: tuple[bool, bool, bool]
    runs_scored: int
    total_runs: int
    contact_quality: float
    crowd_energy_before: float
    crowd_energy_after: float
    crowd_modifiers: Dict[str, float]
    context_modifiers: Dict[str, float]
    modifier_flags: Dict[str, bool]

    def as_payload(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "outcome": {
                "result": self.outcome,
                "detail": self.detail,
                "contact_quality": self.contact_quality,
                "runs_scored": self.runs_scored,
                "total_runs": self.total_runs,
            },
            "context": {
                "pitch_number": self.number,
                "batter": self.batter,
                "count": {
                    "before": {"balls": self.balls_before, "strikes": self.strikes_before},
                    "after": {"balls": self.balls_after, "strikes": self.strikes_after},
                },
                "outs": {"before": self.outs_before, "after": self.outs_after},
                "bases": {
                    "before": list(self.bases_before),
                    "after": list(self.bases_after),
                },
                "crowd": {
                    "energy_before": self.crowd_energy_before,
                    "energy_after": self.crowd_energy_after,
                },
            },
        }

        modifiers: Dict[str, object] = {
            "applied": dict(self.context_modifiers),
            "crowd": dict(self.crowd_modifiers),
            "flags": dict(self.modifier_flags),
        }

        if self.context_modifiers or self.crowd_modifiers or any(self.modifier_flags.values()):
            payload["modifiers"] = modifiers

        return payload

    def as_dict(self) -> Dict[str, object]:
        # Maintain backwards compatibility for JSON dumping callers while
        # enforcing the standardized payload format.
        return self.as_payload()


class HalfInningState:
    """Track a single half-inning and log every pitch."""

    def __init__(
        self,
        lineup: Sequence[Dict[str, object]],
        defense: DefenseRatings,
        pitcher: PitcherRatings,
        situational_modifiers: Optional[Dict[str, float]] = None,
        seed: Optional[int] = None,
        *,
        loggers: Optional[Sequence[Callable[[Dict[str, object]], None]]] = None,
        enable_crowd_effects: bool = True,
        enable_stadium_effects: bool = True,
        enable_organ_flair: bool = False,
    ) -> None:
        self.lineup = lineup
        self.pitcher = pitcher
        self.defense = defense
        self.base_modifiers = situational_modifiers or {}
        self.balls = 0
        self.strikes = 0
        self.outs = 0
        self.bases: tuple[bool, bool, bool] = (False, False, False)
        self.runs = 0
        self.batter_index = 0
        self.pitch_number = 0
        self.events: List[PitchEvent] = []
        self.replay_log: List[Dict[str, object]] = []
        self._rng = random.Random(seed)
        self.crowd = CrowdEnergyAccumulator()
        self._loggers: List[Callable[[Dict[str, object]], None]] = list(loggers or [])
        self._modifier_flags = {
            "crowd": enable_crowd_effects,
            "stadium": enable_stadium_effects,
            "organ": enable_organ_flair,
        }

    def _current_batter(self) -> Dict[str, object]:
        return self.lineup[self.batter_index % len(self.lineup)]

    def _participants(self) -> PitchParticipants:
        batter = self._current_batter()
        batter_ratings: BatterRatings = batter["ratings"]
        return PitchParticipants(
            pitcher=self.pitcher,
            batter=batter_ratings,
            defense=self.defense,
        )

    def _context(self, modifiers: Optional[Dict[str, float]] = None) -> PitchContext:
        return PitchContext(
            balls=self.balls,
            strikes=self.strikes,
            outs=self.outs,
            bases=self.bases,
            situational_modifiers=modifiers if modifiers is not None else self._effective_modifiers(),
        )

    def _effective_modifiers(
        self, crowd_snapshot: Optional[CrowdEnergySnapshot] = None
    ) -> Dict[str, float]:
        effective: Dict[str, float] = {}

        if self._modifier_flags["stadium"]:
            effective.update(self.base_modifiers)

        if self._modifier_flags["crowd"]:
            crowd_state = crowd_snapshot or self.crowd.snapshot()
            for key, value in crowd_state.modifiers.items():
                effective[key] = effective.get(key, 0.0) + value

        organ_modifier = self._organ_modifier(crowd_snapshot)
        if organ_modifier and self._modifier_flags["organ"]:
            effective["organ"] = effective.get("organ", 0.0) + organ_modifier

        return effective

    def _organ_modifier(self, crowd_snapshot: Optional[CrowdEnergySnapshot]) -> float:
        if not self._modifier_flags["organ"]:
            return 0.0

        reference = crowd_snapshot or self.crowd.snapshot()
        momentum = reference.energy / max(self.crowd.max_energy, 1.0)
        # The organ should never dominate the simulation; it gently nudges hitters
        # when the crowd is already buzzing.
        return min(0.02, 0.01 + 0.03 * momentum)

    def _advance_batter(self) -> None:
        self.balls = 0
        self.strikes = 0
        self.batter_index += 1

    def _record_out(self) -> None:
        self.outs += 1
        self._advance_batter()

    def _walk_batter(self) -> int:
        runs = 0
        new_bases = [False, False, False]
        first, second, third = self.bases

        if third and second and first:
            runs += 1
        elif third:
            new_bases[2] = True

        if second and first:
            new_bases[2] = True
        elif second:
            new_bases[1] = True

        if first:
            new_bases[1] = True

        new_bases[0] = True

        self.bases = tuple(new_bases)
        self._advance_batter()
        return runs

    def _advance_runners(self, bases_taken: int) -> int:
        runs = 0
        new_bases = [False, False, False]
        for idx in range(2, -1, -1):
            if self.bases[idx]:
                destination = idx + bases_taken
                if destination >= 3:
                    runs += 1
                else:
                    new_bases[destination] = True
        if bases_taken < 4:
            destination = bases_taken - 1
            if destination >= 0:
                new_bases[destination] = True
        else:
            runs += 1
        self.bases = tuple(new_bases)
        self._advance_batter()
        return runs

    def _log_payload(self, payload: Dict[str, object]) -> None:
        snapshot = deepcopy(payload)
        self.replay_log.append(snapshot)
        for logger in self._loggers:
            logger(deepcopy(snapshot))

    def pitch_once(self, seed: Optional[int] = None) -> PitchEvent:
        participants = self._participants()
        decayed_snapshot = self.crowd.tick() if self._modifier_flags["crowd"] else self.crowd.snapshot()
        context_modifiers = self._effective_modifiers(decayed_snapshot)
        context = self._context(context_modifiers)
        outcome = resolve_pitch_outcome(
            participants, context, rng=self._rng if seed is None else None, seed=seed
        )

        self.pitch_number += 1
        batter_name = self._current_batter().get("name", "Unknown")
        pre_bases = self.bases
        pre_balls = self.balls
        pre_strikes = self.strikes
        pre_outs = self.outs

        applied_result = outcome.result
        runs_scored = 0

        if outcome.result == "ball":
            self.balls += 1
            if self.balls >= 4:
                runs_scored = self._walk_batter()
                applied_result = "walk"
        elif outcome.result in {"called_strike", "swinging_strike"}:
            self.strikes += 1
            if self.strikes >= 3:
                self._record_out()
                applied_result = "strikeout"
        elif outcome.result == "foul":
            if self.strikes < 2:
                self.strikes += 1
        elif outcome.result == "inplay_out":
            self._record_out()
            applied_result = "inplay_out"
        elif outcome.result in {"single", "double", "triple", "homerun"}:
            bases_taken = {"single": 1, "double": 2, "triple": 3, "homerun": 4}[outcome.result]
            runs_scored = self._advance_runners(bases_taken)
            applied_result = outcome.result
        else:
            applied_result = outcome.result

        self.runs += runs_scored
        updated_crowd = (
            self.crowd.apply_event(applied_result, runs_scored, outcome.contact_quality)
            if self._modifier_flags["crowd"]
            else decayed_snapshot
        )

        event = PitchEvent(
            number=self.pitch_number,
            batter=batter_name,
            outcome=applied_result,
            detail=outcome.description,
            balls_before=pre_balls,
            strikes_before=pre_strikes,
            outs_before=pre_outs,
            balls_after=self.balls,
            strikes_after=self.strikes,
            outs_after=self.outs,
            bases_before=pre_bases,
            bases_after=self.bases,
            runs_scored=runs_scored,
            total_runs=self.runs,
            contact_quality=outcome.contact_quality,
            crowd_energy_before=decayed_snapshot.energy,
            crowd_energy_after=updated_crowd.energy,
            crowd_modifiers=updated_crowd.modifiers if self._modifier_flags["crowd"] else {},
            context_modifiers=dict(context_modifiers),
            modifier_flags=dict(self._modifier_flags),
        )
        self.events.append(event)
        self._log_payload(event.as_payload())
        return event

    def is_complete(self) -> bool:
        return self.outs >= 3

    def play_to_completion(self, max_pitches: int = 100) -> List[PitchEvent]:
        while not self.is_complete() and self.pitch_number < max_pitches:
            self.pitch_once()
        return self.events

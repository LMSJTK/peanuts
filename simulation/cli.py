"""Minimal CLI harness to run a scripted half-inning for debugging."""

from __future__ import annotations

import argparse
import json
from typing import List

from .fixtures import SAMPLE_BATTER, SAMPLE_DEFENSE, SAMPLE_PITCHER, SAMPLE_STADIUM
from .state import HalfInningState


def build_lineup(size: int = 3) -> List[dict]:
    return [SAMPLE_BATTER for _ in range(size)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a sample half-inning simulation")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for deterministic output")
    parser.add_argument("--max-pitches", type=int, default=120, help="Fail-safe pitch cap")
    parser.add_argument("--json", action="store_true", help="Emit JSON replay data instead of text")
    args = parser.parse_args()

    lineup = build_lineup()
    state = HalfInningState(
        lineup=lineup,
        defense=SAMPLE_DEFENSE,
        pitcher=SAMPLE_PITCHER["ratings"],
        situational_modifiers=SAMPLE_STADIUM["modifiers"],
        seed=args.seed,
    )

    state.play_to_completion(max_pitches=args.max_pitches)

    if args.json:
        print(json.dumps([event.as_dict() for event in state.events], indent=2))
        return

    print(f"Stadium: {SAMPLE_STADIUM['name']}")
    print(f"Pitcher: {SAMPLE_PITCHER['name']}")
    print(f"Lineup: {[p['name'] for p in lineup]}")
    print("---")
    for event in state.events:
        pre_count = f"{event.balls_before}-{event.strikes_before}"
        post_count = f"{event.balls_after}-{event.strikes_after}"
        bases_before = "".join(["1" if base else "-" for base in event.bases_before])
        bases_after = "".join(["1" if base else "-" for base in event.bases_after])
        print(
            f"Pitch {event.number:02d} | {event.batter} | {event.outcome:<10} | "
            f"count {pre_count} -> {post_count} | outs {event.outs_before}->{event.outs_after} | "
            f"bases {bases_before}->{bases_after} | runs +{event.runs_scored} (total {event.total_runs}) | {event.detail}"
        )

    print("---")
    print(f"Half-inning complete. Runs scored: {state.runs}")


if __name__ == "__main__":
    main()

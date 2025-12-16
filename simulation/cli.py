"""Minimal CLI harness to run scripted half-innings or full games for debugging."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from .fixtures import SAMPLE_BATTER, SAMPLE_DEFENSE, SAMPLE_PITCHER, SAMPLE_STADIUM
from .state import GameState, HalfInningState


def build_lineup(size: int = 3) -> List[dict]:
    return [SAMPLE_BATTER for _ in range(size)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a sample half-inning simulation")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for deterministic output")
    parser.add_argument("--max-pitches", type=int, default=120, help="Fail-safe pitch cap")
    parser.add_argument("--json", action="store_true", help="Emit JSON replay data instead of text")
    parser.add_argument("--full-game", action="store_true", help="Play a full game instead of a half-inning")
    parser.add_argument("--game-id", type=str, default="sample-game", help="Identifier to tag the box score")
    parser.add_argument("--home-team", type=str, default="Home Team", help="Label for the home team")
    parser.add_argument("--away-team", type=str, default="Away Team", help="Label for the away team")
    parser.add_argument("--lineup-size", type=int, default=3, help="Number of batters to include in each lineup")
    parser.add_argument("--max-innings", type=int, default=9, help="Regulation innings to schedule")
    parser.add_argument("--max-extra-innings", type=int, default=3, help="Cap on extra innings before declaring a draw")
    parser.add_argument("--season-year", type=int, default=0, help="Season year to stamp in persisted box scores")
    parser.add_argument(
        "--season-state-path",
        type=str,
        default=None,
        help="Optional path to write a SeasonState containing the box score",
    )
    parser.add_argument(
        "--replay-log",
        type=str,
        default=None,
        help="Write the combined replay log to the provided path for viewer playback",
    )
    parser.add_argument(
        "--disable-crowd-effects",
        action="store_true",
        help="Ignore crowd-driven modifiers during simulation",
    )
    parser.add_argument(
        "--disable-stadium-effects",
        action="store_true",
        help="Ignore base stadium modifiers during simulation",
    )
    parser.add_argument(
        "--enable-organ-flair",
        action="store_true",
        help="Allow the optional organ agent to add small situational boosts",
    )
    args = parser.parse_args()

    lineup = build_lineup(args.lineup_size)

    if args.full_game:
        game = GameState(
            game_id=args.game_id,
            home_team=args.home_team,
            away_team=args.away_team,
            home_lineup=lineup,
            away_lineup=build_lineup(args.lineup_size),
            home_pitcher=SAMPLE_PITCHER["ratings"],
            away_pitcher=SAMPLE_PITCHER["ratings"],
            home_defense=SAMPLE_DEFENSE,
            away_defense=SAMPLE_DEFENSE,
            stadium_modifiers=SAMPLE_STADIUM["modifiers"],
            seed=args.seed,
            max_innings=args.max_innings,
            max_extra_innings=args.max_extra_innings,
            max_half_inning_pitches=args.max_pitches,
            enable_crowd_effects=not args.disable_crowd_effects,
            enable_stadium_effects=not args.disable_stadium_effects,
            enable_organ_flair=args.enable_organ_flair,
        )

        summary = game.play_game()

        if args.replay_log:
            Path(args.replay_log).write_text(json.dumps(game.as_replay_payload(), indent=2), encoding="utf-8")

        if args.season_state_path:
            game.persist_box_score(season_year=args.season_year, destination=args.season_state_path)

        if args.json:
            print(json.dumps(summary.to_dict(), indent=2))
            return

        print(f"Game: {args.away_team} at {args.home_team} ({args.game_id})")
        print(f"Stadium: {SAMPLE_STADIUM['name']}")
        print("---")
        for idx, (away_runs, home_runs) in enumerate(summary.inning_lines, start=1):
            print(f"Inning {idx:02d} | Away {away_runs} | Home {home_runs}")
        print("---")
        print(f"Final: {args.away_team} {summary.away_score} - {args.home_team} {summary.home_score}")
        return

    state = HalfInningState(
        lineup=lineup,
        defense=SAMPLE_DEFENSE,
        pitcher=SAMPLE_PITCHER["ratings"],
        situational_modifiers=SAMPLE_STADIUM["modifiers"],
        seed=args.seed,
        enable_crowd_effects=not args.disable_crowd_effects,
        enable_stadium_effects=not args.disable_stadium_effects,
        enable_organ_flair=args.enable_organ_flair,
    )

    state.play_to_completion(max_pitches=args.max_pitches)

    if args.json:
        print(json.dumps(state.replay_log, indent=2))
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

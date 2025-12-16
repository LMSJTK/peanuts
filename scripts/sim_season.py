"""Run a configurable batch of simulated games and assert safety invariants."""
from __future__ import annotations

import argparse
import json
import random
from collections import deque
from dataclasses import asdict, replace
from pathlib import Path
from typing import Deque, Dict, Iterable, List, MutableMapping, Sequence

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulation.fixtures import SAMPLE_BATTER, SAMPLE_DEFENSE, SAMPLE_PITCHER, SAMPLE_STADIUM
from simulation.management_bridge import load_management_state
from simulation.persistence import FinanceLedger, SeasonState, TeamStanding, save_season_state
from simulation.state import GameState

DEFAULT_GAMES = 50
DEFAULT_SERIES_LENGTH = 3
CROWD_CAP = 0.08
CROWD_MAX = 100.0
RECOVERY_PER_GAME = 50


def _rated_lineup(entries: Sequence[MutableMapping[str, object]]) -> List[Dict[str, object]]:
    """Apply the sample batter ratings to every lineup slot while preserving names."""

    template = SAMPLE_BATTER["ratings"]
    return [{"name": entry.get("name", "Unknown"), "ratings": template} for entry in entries]


def _rotation_names(entries: Sequence[MutableMapping[str, object]], fallback: str) -> List[str]:
    names = [entry.get("name", fallback) for entry in entries]
    return names or [fallback]


def _rotate_lineup(lineup: Sequence[Dict[str, object]], offset: int) -> List[Dict[str, object]]:
    rotated: Deque[Dict[str, object]] = deque(lineup)
    rotated.rotate(-offset)
    return list(rotated)


def _count_team_pitches(replay_log: Iterable[MutableMapping[str, object]], batting_team: str) -> int:
    count = 0
    for payload in replay_log:
        half = payload.get("half_inning", {}) or {}
        if half.get("batting_team") == batting_team:
            count += 1
    return count


def _validate_crowd_modifiers(replay_log: Iterable[MutableMapping[str, object]]) -> None:
    for payload in replay_log:
        modifiers = (payload.get("modifiers") or {}).get("crowd", {})
        context_crowd = (payload.get("context") or {}).get("crowd", {})
        before = float(context_crowd.get("energy_before", 0.0))
        after = float(context_crowd.get("energy_after", 0.0))

        if before < 0 or after < 0 or before > CROWD_MAX or after > CROWD_MAX:
            raise AssertionError(f"Crowd energy exceeded bounds: before={before}, after={after}")

        for key, value in modifiers.items():
            if value < -CROWD_CAP or value > CROWD_CAP:
                raise AssertionError(f"Crowd modifier {key} out of bounds: {value}")


def _apply_series_economics(ledger: FinanceLedger, series_length: int) -> Dict[str, float]:
    promo_multiplier = 1 + 0.05 * len(ledger.promotions)
    gate_revenue = ledger.ticket_price * 1000 * series_length * promo_multiplier
    concessions_revenue = sum(ledger.concessions_pricing.values()) * 75 * series_length
    recurring_revenue = sum(ledger.revenue.values())
    recurring_expenses = sum(ledger.expenses.values())
    upkeep = 5000 * series_length

    revenue = gate_revenue + concessions_revenue + recurring_revenue
    expenses = recurring_expenses + upkeep

    ledger.cash_on_hand += revenue - expenses

    if ledger.cash_on_hand < 0:
        raise AssertionError("Budget dipped below zero after economic adjustments")

    return {
        "gate_revenue": gate_revenue,
        "concessions_revenue": concessions_revenue,
        "recurring_revenue": recurring_revenue,
        "recurring_expenses": recurring_expenses,
        "upkeep": upkeep,
        "ending_cash": ledger.cash_on_hand,
    }


def _rest_rotation(fatigue: Dict[str, float], *, reset: bool = False) -> None:
    for name, current in list(fatigue.items()):
        fatigue[name] = 0.0 if reset else max(0.0, current - RECOVERY_PER_GAME)


def _record_standings(standings: Dict[str, TeamStanding], summary, home_team: str, away_team: str) -> None:
    home = standings.setdefault(home_team, TeamStanding(team_id=home_team, wins=0, losses=0))
    away = standings.setdefault(away_team, TeamStanding(team_id=away_team, wins=0, losses=0))

    home.runs_for += summary.home_score
    home.runs_against += summary.away_score
    away.runs_for += summary.away_score
    away.runs_against += summary.home_score

    if summary.home_score > summary.away_score:
        home.wins += 1
        away.losses += 1
    elif summary.home_score < summary.away_score:
        away.wins += 1
        home.losses += 1


def _serialize_finances(ledger: FinanceLedger) -> Dict[str, object]:
    payload = asdict(ledger)
    payload["revenue"] = dict(payload.get("revenue", {}))
    payload["expenses"] = dict(payload.get("expenses", {}))
    payload["promotions"] = list(payload.get("promotions", []))
    payload["concessions_pricing"] = dict(payload.get("concessions_pricing", {}))
    return payload


def run_simulated_season(
    *,
    games: int,
    series_length: int,
    season_year: int,
    seed: int | None = None,
    season_state_path: Path | None = None,
) -> Dict[str, object]:
    rng = random.Random(seed)
    manager_state = load_management_state()

    home_lineup_template = _rated_lineup(manager_state.lineup)
    away_lineup_template = list(reversed(home_lineup_template))

    rotation = _rotation_names(manager_state.rotation, SAMPLE_PITCHER["name"])
    away_rotation = list(reversed(rotation)) or rotation

    home_ledger = replace(manager_state.ledger)
    away_ledger = FinanceLedger(
        cash_on_hand=200_000.0,
        revenue={"gate": 110_000.0},
        expenses={"travel": 25_000.0},
        ticket_price=22.0,
        promotions=["familyDay"],
        concessions_pricing={"Snacks": 5.5, "Soda": 4.0},
    )

    season_state = SeasonState.empty(season_year)
    standings: Dict[str, TeamStanding] = {}
    fatigue_tracker: Dict[str, float] = {name: 0.0 for name in rotation + away_rotation}

    economics_log: List[Dict[str, float]] = []

    for game_index in range(games):
        series_index = game_index // series_length
        series_game = game_index % series_length

        home_lineup = _rotate_lineup(home_lineup_template, series_game)
        away_lineup = _rotate_lineup(away_lineup_template, (series_game + 1) % len(away_lineup_template))

        home_pitcher_name = rotation[game_index % len(rotation)]
        away_pitcher_name = away_rotation[game_index % len(away_rotation)]

        game = GameState(
            game_id=f"season-game-{game_index+1:03d}",
            home_team=manager_state.team_name,
            away_team="Rival Club",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            home_pitcher=SAMPLE_PITCHER["ratings"],
            away_pitcher=SAMPLE_PITCHER["ratings"],
            home_defense=SAMPLE_DEFENSE,
            away_defense=SAMPLE_DEFENSE,
            stadium_modifiers=SAMPLE_STADIUM["modifiers"],
            seed=rng.randint(0, 1_000_000),
            enable_organ_flair=True,
        )

        summary = game.play_game()
        _record_standings(standings, summary, manager_state.team_name, "Rival Club")

        _validate_crowd_modifiers(game.replay_log)

        home_pitches = _count_team_pitches(game.replay_log, batting_team="Rival Club")
        away_pitches = _count_team_pitches(game.replay_log, batting_team=manager_state.team_name)

        fatigue_tracker[home_pitcher_name] += home_pitches
        fatigue_tracker[away_pitcher_name] += away_pitches

        for name in fatigue_tracker:
            if name not in {home_pitcher_name, away_pitcher_name}:
                _rest_rotation(fatigue_tracker, reset=False)
                break

        season_state.box_scores.append(summary)

        if (game_index + 1) % series_length == 0:
            economics_log.append(_apply_series_economics(home_ledger, series_length))
            economics_log.append(_apply_series_economics(away_ledger, series_length))
            _rest_rotation(fatigue_tracker, reset=True)
            if any(value != 0 for value in fatigue_tracker.values()):
                raise AssertionError("Fatigue failed to reset after rest period")

    _rest_rotation(fatigue_tracker, reset=True)
    if any(value != 0 for value in fatigue_tracker.values()):
        raise AssertionError("Fatigue failed to reset after season wrap")

    season_state.standings = list(standings.values())
    season_state.finances = {
        manager_state.team_id: home_ledger,
        "rival-club": away_ledger,
    }
    season_state.stadium_upgrades = {}
    season_state.concessions_pricing = {
        manager_state.team_id: dict(manager_state.ledger.concessions_pricing),
        "rival-club": dict(away_ledger.concessions_pricing),
    }

    if season_state_path:
        save_season_state(season_state, season_state_path)

    return {
        "games": games,
        "series_length": series_length,
        "seed": seed,
        "economics": economics_log,
        "standings": [asdict(entry) for entry in season_state.standings],
        "finances": {
            manager_state.team_id: _serialize_finances(home_ledger),
            "rival-club": _serialize_finances(away_ledger),
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate a configurable stretch of the season")
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES, help="Number of games to play")
    parser.add_argument(
        "--series-length",
        type=int,
        default=DEFAULT_SERIES_LENGTH,
        help="Games per series before applying economics and rest",
    )
    parser.add_argument("--season-year", type=int, default=2024, help="Year tag for persisted box scores")
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed for reproducibility")
    parser.add_argument(
        "--season-state-path",
        type=Path,
        default=Path("tmp/season_state_long.json"),
        help="Destination for the persisted SeasonState payload",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("tmp/season_summary.json"),
        help="Where to write the high-level summary report",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_simulated_season(
        games=args.games,
        series_length=args.series_length,
        seed=args.seed,
        season_year=args.season_year,
        season_state_path=args.season_state_path,
    )

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Simulated {summary['games']} games across series of {summary['series_length']}")
    print(f"Season state written to: {args.season_state_path}")
    print(f"Summary report written to: {args.summary}")
    print("Final standings:")
    for entry in summary["standings"]:
        print(
            f"- {entry['team_id']}: {entry['wins']}-{entry['losses']} "
            f"(RF {entry['runs_for']} / RA {entry['runs_against']})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

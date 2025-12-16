"""Development helper to refresh the replay feed and serve the viewer."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulation.cli import build_lineup
from simulation.fixtures import SAMPLE_DEFENSE, SAMPLE_PITCHER, SAMPLE_STADIUM
from simulation.state import GameState, HalfInningState


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_payload(args: argparse.Namespace) -> dict:
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
        game.play_game()
        payload = game.as_replay_payload()
    else:
        half = HalfInningState(
            lineup=lineup,
            defense=SAMPLE_DEFENSE,
            pitcher=SAMPLE_PITCHER["ratings"],
            situational_modifiers=SAMPLE_STADIUM["modifiers"],
            seed=args.seed,
            enable_crowd_effects=not args.disable_crowd_effects,
            enable_stadium_effects=not args.disable_stadium_effects,
            enable_organ_flair=args.enable_organ_flair,
        )
        half.play_to_completion(max_pitches=args.max_pitches)
        payload = {
            "game_id": args.game_id,
            "home_team": args.home_team,
            "away_team": args.away_team,
            "half_inning": args.half_inning,
            "events": list(half.replay_log),
        }

    payload["updated_at"] = _timestamp()
    return payload


def write_feed(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def start_server(directory: Path, port: int) -> ThreadingHTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def run_once(args: argparse.Namespace) -> None:
    payload = generate_payload(args)
    write_feed(payload, Path(args.output))
    print(f"Wrote replay feed with {len(payload.get('events', []))} events to {args.output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a replay feed and serve the viewer")
    parser.add_argument("--full-game", action="store_true", help="Play a full game instead of a single half-inning")
    parser.add_argument("--lineup-size", type=int, default=3, help="Number of batters in each lineup")
    parser.add_argument("--max-pitches", type=int, default=120, help="Fail-safe pitch cap for each half-inning")
    parser.add_argument("--max-innings", type=int, default=9, help="Regulation innings for full games")
    parser.add_argument("--max-extra-innings", type=int, default=3, help="Cap on extra innings before a draw")
    parser.add_argument("--game-id", type=str, default="dev-game", help="Identifier for the simulated contest")
    parser.add_argument("--home-team", type=str, default="Home Team", help="Label for the home team")
    parser.add_argument("--away-team", type=str, default="Away Team", help="Label for the away team")
    parser.add_argument("--half-inning", type=str, default="top", help="Half-inning label when not simulating a full game")
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed for deterministic output")
    parser.add_argument("--disable-crowd-effects", action="store_true", help="Ignore crowd modifiers during simulation")
    parser.add_argument("--disable-stadium-effects", action="store_true", help="Ignore stadium modifiers during simulation")
    parser.add_argument("--enable-organ-flair", action="store_true", help="Allow the optional organ agent to add small boosts")
    parser.add_argument("--output", type=Path, default=Path("web/replay.json"), help="Where to write the replay feed")
    parser.add_argument("--serve", action="store_true", help="Serve the /web directory with a lightweight HTTP server")
    parser.add_argument("--port", type=int, default=8000, help="Port for the dev HTTP server")
    parser.add_argument("--watch", action="store_true", help="Press Enter to re-run the sim and refresh the feed")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    web_dir = Path(args.output).resolve().parent
    server = start_server(web_dir, args.port) if args.serve else None
    if server:
        print(f"Serving {web_dir} at http://localhost:{args.port} (Ctrl+C to stop)")

    run_once(args)

    if args.watch:
        print("Press Enter to re-run the simulation and refresh the viewer feed.")
        try:
            while True:
                input()
                run_once(args)
        except KeyboardInterrupt:
            pass
    elif server:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    if server:
        server.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())

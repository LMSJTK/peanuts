"""Generate deterministic end-to-end artifacts for simulation and viewer tests."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict

DEFAULT_SEED = 42
DEFAULT_ARTIFACT_DIR = Path("tmp/e2e")


def run_cli(seed: int, artifact_dir: Path) -> Dict[str, Path]:
    artifact_dir.mkdir(parents=True, exist_ok=True)

    replay_path = artifact_dir / "replay_log.json"
    season_state_path = artifact_dir / "season_state.json"
    box_score_path = artifact_dir / "box_score_summary.json"

    cmd = [
        sys.executable,
        "-m",
        "simulation.cli",
        "--full-game",
        "--json",
        f"--seed={seed}",
        f"--replay-log={replay_path}",
        f"--season-state-path={season_state_path}",
        "--game-id",
        "e2e-sample",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    summary = json.loads(result.stdout)
    box_score_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "replay": replay_path,
        "season_state": season_state_path,
        "box_score": box_score_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a seeded full game and capture artifacts.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Seed for deterministic simulation output")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help="Directory to store generated artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifacts = run_cli(seed=args.seed, artifact_dir=args.artifact_dir)
    print("Generated artifacts:")
    for name, path in artifacts.items():
        print(f"- {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import math
import numbers
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = PROJECT_ROOT / "tmp/e2e"
GOLDEN_DIR = PROJECT_ROOT / "tests" / "fixtures"
GOLDEN_REPLAY = GOLDEN_DIR / "e2e_replay_log.json"
GOLDEN_BOX = GOLDEN_DIR / "e2e_box_score_summary.json"

NUMERIC_TOLERANCE = 1e-6


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_structures_close(actual: Any, expected: Any, *, path: str = "root") -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path} expected dict got {type(actual)}"
        assert set(actual.keys()) == set(expected.keys()), f"{path} keys differ"
        for key in expected:
            assert_structures_close(actual[key], expected[key], path=f"{path}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list), f"{path} expected list got {type(actual)}"
        assert len(actual) == len(expected), f"{path} length mismatch"
        for idx, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            assert_structures_close(actual_item, expected_item, path=f"{path}[{idx}]")
    elif isinstance(expected, numbers.Number):
        assert isinstance(actual, numbers.Number), f"{path} expected numeric got {type(actual)}"
        assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=NUMERIC_TOLERANCE), (
            f"{path} mismatch: {actual} vs {expected}"
        )
    else:
        assert actual == expected, f"{path} mismatch: {actual} vs {expected}"


@pytest.fixture(scope="session")
def e2e_artifacts() -> dict[str, Path]:
    subprocess.run(
        [sys.executable, "scripts/run_e2e.py", "--seed", "42"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    return {
        "replay": ARTIFACT_DIR / "replay_log.json",
        "box_score": ARTIFACT_DIR / "box_score_summary.json",
    }


def test_replay_matches_golden_snapshot(e2e_artifacts: dict[str, Path]) -> None:
    actual = load_json(e2e_artifacts["replay"])
    expected = load_json(GOLDEN_REPLAY)
    assert_structures_close(actual, expected)


def test_box_score_matches_golden_snapshot(e2e_artifacts: dict[str, Path]) -> None:
    actual = load_json(e2e_artifacts["box_score"])
    expected = load_json(GOLDEN_BOX)
    assert_structures_close(actual, expected)

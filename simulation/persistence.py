"""Persistence helpers for season state and economic levers."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, List, MutableMapping, Optional

SEASON_STATE_VERSION = "1.0.0"

Migration = Callable[[MutableMapping[str, object]], MutableMapping[str, object]]


@dataclass
class TeamStanding:
    team_id: str
    wins: int
    losses: int
    runs_for: int = 0
    runs_against: int = 0

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: MutableMapping[str, object]) -> "TeamStanding":
        return cls(
            team_id=str(data["team_id"]),
            wins=int(data.get("wins", 0)),
            losses=int(data.get("losses", 0)),
            runs_for=int(data.get("runs_for", 0)),
            runs_against=int(data.get("runs_against", 0)),
        )


@dataclass
class BoxScoreSummary:
    game_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    inning_lines: Optional[List[List[int]]] = None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["inning_lines"] = self.inning_lines or []
        return payload

    @classmethod
    def from_dict(cls, data: MutableMapping[str, object]) -> "BoxScoreSummary":
        return cls(
            game_id=str(data["game_id"]),
            home_team=str(data["home_team"]),
            away_team=str(data["away_team"]),
            home_score=int(data.get("home_score", 0)),
            away_score=int(data.get("away_score", 0)),
            inning_lines=[list(map(int, row)) for row in data.get("inning_lines", [])],
        )


@dataclass
class FinanceLedger:
    cash_on_hand: float
    revenue: Dict[str, float]
    expenses: Dict[str, float]
    ticket_price: float
    promotions: List[str]
    concessions_pricing: Dict[str, float]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: MutableMapping[str, object]) -> "FinanceLedger":
        return cls(
            cash_on_hand=float(data.get("cash_on_hand", 0.0)),
            revenue={k: float(v) for k, v in dict(data.get("revenue", {})).items()},
            expenses={k: float(v) for k, v in dict(data.get("expenses", {})).items()},
            ticket_price=float(data.get("ticket_price", 0.0)),
            promotions=list(data.get("promotions", [])),
            concessions_pricing={
                k: float(v) for k, v in dict(data.get("concessions_pricing", {})).items()
            },
        )


@dataclass
class StadiumUpgrade:
    name: str
    level: int
    effect: str
    cost: float

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: MutableMapping[str, object]) -> "StadiumUpgrade":
        return cls(
            name=str(data["name"]),
            level=int(data.get("level", 1)),
            effect=str(data.get("effect", "")),
            cost=float(data.get("cost", 0.0)),
        )


@dataclass
class SeasonState:
    """Bundle the season state for persistence and migration."""

    season_year: int
    standings: List[TeamStanding]
    box_scores: List[BoxScoreSummary]
    finances: Dict[str, FinanceLedger]
    stadium_upgrades: Dict[str, List[StadiumUpgrade]]
    concessions_pricing: Dict[str, Dict[str, float]]
    version: str = SEASON_STATE_VERSION

    def to_dict(self) -> Dict[str, object]:
        return {
            "version": self.version,
            "season_year": self.season_year,
            "standings": [team.to_dict() for team in self.standings],
            "box_scores": [box.to_dict() for box in self.box_scores],
            "finances": {team: ledger.to_dict() for team, ledger in self.finances.items()},
            "stadium_upgrades": {
                team: [upgrade.to_dict() for upgrade in upgrades]
                for team, upgrades in self.stadium_upgrades.items()
            },
            "concessions_pricing": {
                team: {item: float(price) for item, price in pricing.items()}
                for team, pricing in self.concessions_pricing.items()
            },
        }

    @classmethod
    def from_dict(cls, data: MutableMapping[str, object]) -> "SeasonState":
        return cls(
            season_year=int(data.get("season_year", 0)),
            standings=[TeamStanding.from_dict(t) for t in data.get("standings", [])],
            box_scores=[BoxScoreSummary.from_dict(b) for b in data.get("box_scores", [])],
            finances={
                team: FinanceLedger.from_dict(ledger)
                for team, ledger in dict(data.get("finances", {})).items()
            },
            stadium_upgrades={
                team: [StadiumUpgrade.from_dict(item) for item in upgrades]
                for team, upgrades in dict(data.get("stadium_upgrades", {})).items()
            },
            concessions_pricing={
                team: {item: float(price) for item, price in dict(pricing).items()}
                for team, pricing in dict(data.get("concessions_pricing", {})).items()
            },
            version=str(data.get("version", SEASON_STATE_VERSION)),
        )

    @classmethod
    def empty(cls, season_year: int) -> "SeasonState":
        return cls(
            season_year=season_year,
            standings=[],
            box_scores=[],
            finances={},
            stadium_upgrades={},
            concessions_pricing={},
        )


MIGRATIONS: Dict[str, Migration] = {}


def apply_migrations(raw: MutableMapping[str, object]) -> MutableMapping[str, object]:
    """Iteratively upgrade payloads using registered migration handlers."""

    current_version = str(raw.get("version", "0.0.0"))
    while current_version in MIGRATIONS:
        raw = MIGRATIONS[current_version](raw)
        current_version = str(raw.get("version", current_version))
    return raw


def save_season_state(state: SeasonState, path: Path | str) -> Path:
    """Persist the provided ``SeasonState`` to disk with a version tag."""

    payload = state.to_dict()
    payload.setdefault("version", SEASON_STATE_VERSION)

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def load_season_state(path: Path | str) -> SeasonState:
    """Load a ``SeasonState`` from disk, applying migrations when required."""

    raw_payload: MutableMapping[str, object] = json.loads(Path(path).read_text(encoding="utf-8"))
    migrated = apply_migrations(raw_payload)
    return SeasonState.from_dict(migrated)


__all__ = [
    "SEASON_STATE_VERSION",
    "TeamStanding",
    "BoxScoreSummary",
    "FinanceLedger",
    "StadiumUpgrade",
    "SeasonState",
    "apply_migrations",
    "save_season_state",
    "load_season_state",
]

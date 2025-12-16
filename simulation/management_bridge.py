"""Bridge helpers for pulling management UI exports into the simulator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, MutableMapping

from .persistence import FinanceLedger

DEFAULT_BRIDGE_PATH = Path(__file__).resolve().parent.parent / "web" / "manager_state.json"


@dataclass
class ManagementBridgeState:
    """Normalized view of the user's roster and finance levers."""

    team_id: str
    team_name: str
    lineup: List[Dict[str, str]]
    rotation: List[Dict[str, str]]
    ledger: FinanceLedger

    def team_payload(self) -> Dict[str, object]:
        """Return a payload compatible with :mod:`simulation.schemas.team_schema`."""

        return {
            "id": self.team_id,
            "name": self.team_name,
            "stadium_id": "home-stadium",
            "market_size": "medium",
            "lineup": [entry["name"] for entry in self.lineup],
            "rotation": [entry["name"] for entry in self.rotation],
            "finance": {
                "cash_on_hand": self.ledger.cash_on_hand,
                "ticket_price": self.ledger.ticket_price,
                "promotions": list(self.ledger.promotions),
                "concessions": dict(self.ledger.concessions_pricing),
            },
        }

    def finance_payload(self) -> Dict[str, object]:
        """Expose the full FinanceLedger payload for persistence."""

        return self.ledger.to_dict()


def _finance_from_payload(payload: MutableMapping[str, object]) -> FinanceLedger:
    economics = payload.get("finance") or payload.get("economics") or {}
    concessions = economics.get("concessions_pricing") or economics.get("concessions") or {}
    return FinanceLedger(
        cash_on_hand=float(economics.get("cash_on_hand", 0.0)),
        revenue={k: float(v) for k, v in dict(economics.get("revenue", {})).items()},
        expenses={k: float(v) for k, v in dict(economics.get("expenses", {})).items()},
        ticket_price=float(economics.get("ticket_price", economics.get("ticketPrice", 0.0))),
        promotions=list(economics.get("promotions", [])),
        concessions_pricing={k: float(v) for k, v in dict(concessions).items()},
    )


def _team_from_payload(payload: MutableMapping[str, object]) -> Dict[str, object]:
    team = payload.get("team") or payload
    return {
        "id": str(team.get("id", "peanuts-user-club")),
        "name": str(team.get("name", payload.get("teamName", "User Club"))),
        "lineup": list(team.get("lineup", [])),
        "rotation": list(team.get("rotation", [])),
    }


def load_management_state(path: Path | str = DEFAULT_BRIDGE_PATH) -> ManagementBridgeState:
    """Load a manager sync file and expose FinanceLedger and roster payloads.

    The management UI exports ``manager_state.json`` beside the web assets. This
    helper is meant to be invoked before each game so the simulator consumes the
    latest lineup, rotation, ticket pricing, promotions, and concessions values.
    """

    payload: MutableMapping[str, object] = json.loads(Path(path).read_text(encoding="utf-8"))
    team = _team_from_payload(payload)
    ledger = _finance_from_payload(payload)

    return ManagementBridgeState(
        team_id=team["id"],
        team_name=team["name"],
        lineup=[{"name": entry.get("name", ""), "position": entry.get("position", "")} for entry in team["lineup"]],
        rotation=[{"name": entry.get("name", ""), "role": entry.get("role", "SP")} for entry in team["rotation"]],
        ledger=ledger,
    )


__all__ = ["ManagementBridgeState", "load_management_state", "DEFAULT_BRIDGE_PATH"]

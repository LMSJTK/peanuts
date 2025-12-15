"""JSON schemas for core simulation documents.

Each schema carries a version marker so that downstream tools can migrate
saves forward as formats evolve. The schemas are intentionally focused on
portable primitives to make them suitable for JSON serialization.
"""

from __future__ import annotations

from typing import Dict

SCHEMA_VERSION = "1.0.0"


def _base_schema(title: str) -> Dict[str, object]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": title,
        "type": "object",
        "properties": {
            "version": {"type": "string", "const": SCHEMA_VERSION},
        },
        "required": ["version"],
        "additionalProperties": False,
    }


def player_schema() -> Dict[str, object]:
    """Schema for an individual player entry."""

    schema = _base_schema("Player")
    schema["properties"].update(
        {
            "id": {"type": "string", "description": "Unique player id"},
            "name": {"type": "string"},
            "handedness": {"type": "string", "enum": ["R", "L", "S"]},
            "positions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "ratings": {
                "type": "object",
                "properties": {
                    "contact": {"type": "number", "minimum": 0},
                    "power": {"type": "number", "minimum": 0},
                    "discipline": {"type": "number", "minimum": 0},
                    "velocity": {"type": "number", "minimum": 0},
                    "control": {"type": "number", "minimum": 0},
                    "deception": {"type": "number", "minimum": 0},
                    "range": {"type": "number", "minimum": 0},
                    "surety": {"type": "number", "minimum": 0},
                },
                "required": ["contact", "power", "discipline"],
                "additionalProperties": False,
            },
            "contracts": {
                "type": "object",
                "properties": {
                    "salary": {"type": "number", "minimum": 0},
                    "years": {"type": "integer", "minimum": 0},
                },
                "additionalProperties": False,
            },
        }
    )
    schema["required"].extend(["id", "name", "handedness", "positions", "ratings"])
    return schema


def stadium_schema() -> Dict[str, object]:
    """Schema for stadium descriptors and upgrade chains."""

    schema = _base_schema("Stadium")
    schema["properties"].update(
        {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "capacity": {"type": "integer", "minimum": 0},
            "modifiers": {
                "type": "object",
                "properties": {
                    "global": {"type": "number"},
                    "power": {"type": "number"},
                    "aggression": {"type": "number"},
                    "contact": {"type": "number"},
                },
                "additionalProperties": False,
            },
            "upgrades": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "level": {"type": "integer", "minimum": 1},
                        "effect": {"type": "string"},
                        "cost": {"type": "number", "minimum": 0},
                    },
                    "required": ["name", "level", "effect"],
                    "additionalProperties": False,
                },
                "default": [],
            },
        }
    )
    schema["required"].extend(["id", "name", "capacity"])
    return schema


def team_schema() -> Dict[str, object]:
    """Schema describing teams, their roster hooks, and economy levers."""

    schema = _base_schema("Team")
    schema["properties"].update(
        {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "market_size": {"type": "string", "enum": ["small", "medium", "large"]},
            "stadium_id": {"type": "string"},
            "lineup": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 9,
            },
            "rotation": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
            },
            "finance": {
                "type": "object",
                "properties": {
                    "cash_on_hand": {"type": "number"},
                    "ticket_price": {"type": "number", "minimum": 0},
                    "promotions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "concessions": {
                        "type": "object",
                        "additionalProperties": {"type": "number", "minimum": 0},
                        "default": {},
                    },
                },
                "required": ["cash_on_hand", "ticket_price"],
                "additionalProperties": False,
            },
        }
    )
    schema["required"].extend(["id", "name", "stadium_id", "lineup", "rotation", "finance"])
    return schema


def schedule_schema() -> Dict[str, object]:
    """Schema for the season schedule and pairing details."""

    schema = _base_schema("Schedule")
    schema["properties"].update(
        {
            "season_year": {"type": "integer"},
            "games": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "date": {"type": "string", "format": "date"},
                        "home_team": {"type": "string"},
                        "away_team": {"type": "string"},
                        "stadium_id": {"type": "string"},
                    },
                    "required": ["id", "date", "home_team", "away_team", "stadium_id"],
                    "additionalProperties": False,
                },
            },
        }
    )
    schema["required"].append("season_year")
    return schema


SCHEMAS: Dict[str, Dict[str, object]] = {
    "player": player_schema(),
    "team": team_schema(),
    "stadium": stadium_schema(),
    "schedule": schedule_schema(),
}

__all__ = ["SCHEMA_VERSION", "SCHEMAS", "player_schema", "team_schema", "stadium_schema", "schedule_schema"]

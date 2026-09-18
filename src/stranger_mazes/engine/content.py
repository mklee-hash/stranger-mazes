"""Loads game content (characters/items/season data) from data/*.json.

Keeping content in JSON — separate from the rule code in this package — is a
deliberate design choice from the spec: new seasons, characters, villains or
items should be addable without touching engine logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> Any:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def load_characters() -> dict[str, dict]:
    return _load("characters.json")


def load_items() -> dict[str, dict]:
    return _load("items.json")


def load_season(season_id: int) -> dict:
    return _load(f"season{season_id}.json")

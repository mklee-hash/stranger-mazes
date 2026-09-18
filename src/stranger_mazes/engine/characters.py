"""CharacterData model — abilities live as data + small hooks in encounters.py,
never hardcoded per-class, so new characters only need a JSON entry."""
from __future__ import annotations

from dataclasses import dataclass

from .content import load_characters as _load_characters_raw


@dataclass
class Character:
    id: str
    name: str
    base_hp: int
    ability: str
    description: str = ""

    # Runtime ability state (reset at the start of each new stage/run).
    ability_used: bool = False
    action_locked: bool = False

    def reset_runtime_state(self) -> None:
        self.ability_used = False
        self.action_locked = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ability_used": self.ability_used,
            "action_locked": self.action_locked,
        }


def load_all_characters() -> dict[str, Character]:
    raw = _load_characters_raw()
    return {
        cid: Character(
            id=cid,
            name=v["name"],
            base_hp=v["base_hp"],
            ability=v["ability"],
            description=v.get("description", ""),
        )
        for cid, v in raw.items()
    }


def get_character(character_id: str) -> Character:
    characters = load_all_characters()
    if character_id not in characters:
        raise KeyError(f"Unknown character: {character_id}")
    return characters[character_id]

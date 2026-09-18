"""Item system: 획득 -> 보관 -> 사용 -> 소모, one common interface for every item.

Effects are data-driven (see data/items.json); this module only knows how to
apply the handful of effect kinds, so adding a new item is a JSON edit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .content import load_items as _load_items_raw


@dataclass
class ItemDef:
    id: str
    name: str
    effect: str
    amount: float = 0
    use_prompt: str = ""


def load_all_items() -> dict[str, ItemDef]:
    raw = _load_items_raw()
    return {
        iid: ItemDef(
            id=iid,
            name=v["name"],
            effect=v["effect"],
            amount=v.get("amount", 0),
            use_prompt=v.get("use_prompt", ""),
        )
        for iid, v in raw.items()
    }


@dataclass
class Inventory:
    """A simple stacking inventory: item_id -> count."""

    counts: dict[str, int] = field(default_factory=dict)

    def add(self, item_id: str, n: int = 1) -> None:
        self.counts[item_id] = self.counts.get(item_id, 0) + n

    def has(self, item_id: str) -> bool:
        return self.counts.get(item_id, 0) > 0

    def consume(self, item_id: str) -> bool:
        if not self.has(item_id):
            return False
        self.counts[item_id] -= 1
        if self.counts[item_id] <= 0:
            del self.counts[item_id]
        return True

    def to_dict(self) -> dict:
        return dict(self.counts)

    @classmethod
    def from_dict(cls, data: dict) -> "Inventory":
        return cls(counts=dict(data or {}))

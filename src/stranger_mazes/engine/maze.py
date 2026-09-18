"""Seed-based maze generation.

Design (from the spec): the maze must always contain a valid path to EXIT,
node types are one of START/PATH/ITEM/ENCOUNTER/EVENT/BOSS/EXIT, and the same
seed must reproduce the same maze.

Implementation: a maze is a sequence of junctions. Whichever of the three
directions (좌/직진/우) the player takes, the walk advances exactly one step
closer to the exit -- so a soft-lock is impossible and EXIT is always
reachable. The direction chosen instead controls the *risk profile* of what
is waiting at that step (좌 = safer, 우 = riskier shortcut, 직진 = balanced),
which is what the spec means by choice affecting risk, not survivability.
Stage-level difficulty (branch/risk growth from Stage 1 -> 5) comes from each
stage's `encounter_chance` / `item_chance` in season*.json.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum


class NodeType(str, Enum):
    START = "START"
    PATH = "PATH"
    ITEM = "ITEM"
    ENCOUNTER = "ENCOUNTER"
    EVENT = "EVENT"
    BOSS = "BOSS"
    EXIT = "EXIT"


DIRECTIONS = ("좌", "직진", "우")

# Multipliers applied to a stage's base encounter/item chance, per direction.
_DIRECTION_BIAS = {
    "좌": {"encounter": 0.7, "item": 1.3},
    "직진": {"encounter": 1.0, "item": 1.0},
    "우": {"encounter": 1.35, "item": 0.7},
}


@dataclass
class Junction:
    index: int
    options: dict[str, NodeType]


@dataclass
class Maze:
    seed: int
    stage_id: int
    junctions: list[Junction] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.junctions)


def generate_maze(stage: dict, seed: int) -> Maze:
    # Combine the run seed with the stage id so every stage gets its own,
    # still-reproducible layout instead of repeating stage 1's rolls.
    rng = random.Random(f"{seed}:{stage['id']}")
    length = stage["length"]
    encounter_chance = stage["encounter_chance"]
    item_chance = stage["item_chance"]
    is_boss_stage = bool(stage.get("boss", False))

    junctions: list[Junction] = []
    for i in range(length):
        is_last = i == length - 1
        options: dict[str, NodeType] = {}
        for direction in DIRECTIONS:
            if is_last:
                options[direction] = NodeType.BOSS if is_boss_stage else NodeType.EXIT
                continue
            bias = _DIRECTION_BIAS[direction]
            enc_p = min(0.9, encounter_chance * bias["encounter"])
            item_p = min(0.9 - enc_p, item_chance * bias["item"])
            event_p = 0.1
            roll = rng.random()
            if roll < enc_p:
                node = NodeType.ENCOUNTER
            elif roll < enc_p + item_p:
                node = NodeType.ITEM
            elif roll < enc_p + item_p + event_p:
                node = NodeType.EVENT
            else:
                node = NodeType.PATH
            options[direction] = node
        junctions.append(Junction(index=i, options=options))
    return Maze(seed=seed, stage_id=stage["id"], junctions=junctions)

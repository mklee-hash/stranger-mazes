"""GameEngine — all game rules live here, deliberately with no I/O.

cli.py (and, later, a web/3D UI) only ever calls methods on GameEngine and
renders what comes back. Nothing here prints or reads input, so a future UI
swap (per the spec: "화면이 바뀌어도 로직은 깨지지 않아야 해") only means
writing a new thin front-end against this same class.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .characters import Character, get_character, load_all_characters
from .items import Inventory, ItemDef, load_all_items
from .maze import Maze, NodeType, generate_maze
from .encounters import (
    Resolution,
    apply_leadership_retry,
    build_quiz_options,
    resolve_fight,
    resolve_preference,
    resolve_quiz,
)


FIGHT_ITEM_EFFECTS = {"fight_bonus", "instant_win_fight"}


@dataclass
class StepOutcome:
    node_type: NodeType
    message: str
    requires: Optional[str] = None  # None | "item_choice" | "action_choice"
    success: Optional[bool] = None  # outcome of a fight/quiz/preference resolution
    game_over: bool = False
    stage_cleared: bool = False
    season_cleared: bool = False


class GameEngine:
    def __init__(self, season_data: dict, seed: Optional[int] = None):
        self.season = season_data
        self.all_characters = load_all_characters()
        self.all_items: dict[str, ItemDef] = load_all_items()

        self.character: Optional[Character] = None
        self.hp: int = 0
        self.max_hp: int = 0
        self.inventory = Inventory()
        self.seed: int = seed if seed is not None else random.randrange(1_000_000_000)
        self.stage_id: int = 1
        self.position: int = 0
        self.maze: Optional[Maze] = None
        self.cleared_stages: set[int] = set()
        self.season_cleared: bool = False
        self.game_over: bool = False

        self._rng = random.Random(self.seed)
        self._pending_item_choice: Optional[list[str]] = None
        self._pending_node: Optional[NodeType] = None
        self._pending_quiz: Optional[dict] = None
        self._pending_pref: Optional[dict] = None

    # ---- setup -----------------------------------------------------
    @property
    def playable_character_ids(self) -> list[str]:
        return list(self.season["playable_characters"])

    def _stage_def(self, stage_id: int) -> dict:
        for s in self.season["stages"]:
            if s["id"] == stage_id:
                return s
        raise KeyError(f"Unknown stage: {stage_id}")

    def start_new_run(self, character_id: str, seed: Optional[int] = None) -> None:
        self.character = get_character(character_id)
        self.character.reset_runtime_state()
        self.max_hp = self.character.base_hp
        self.hp = self.max_hp
        self.inventory = Inventory()
        self.stage_id = 1
        self.cleared_stages = set()
        self.season_cleared = False
        self.game_over = False
        if seed is not None:
            self.seed = seed
        self._rng = random.Random(f"{self.seed}:runtime")
        self._start_stage(self.stage_id)

    def _start_stage(self, stage_id: int) -> None:
        self.stage_id = stage_id
        stage = self._stage_def(stage_id)
        self.maze = generate_maze(stage, self.seed)
        self.position = 0
        self.character.reset_runtime_state()
        self._clear_pending()

    def _clear_pending(self) -> None:
        self._pending_item_choice = None
        self._pending_node = None
        self._pending_quiz = None
        self._pending_pref = None

    # ---- state for the UI -------------------------------------------
    @property
    def stage_name(self) -> str:
        return self._stage_def(self.stage_id)["name"]

    @property
    def stage_length(self) -> int:
        return self.maze.length

    def current_junction_options(self) -> dict:
        return dict(self.maze.junctions[self.position].options)

    @property
    def pending_item_choices(self) -> Optional[list[str]]:
        return self._pending_item_choice

    # ---- non-combat item use (available while standing at a junction) --
    def use_waffle(self) -> str:
        if not self.inventory.consume("waffle"):
            raise ValueError("와플이 없습니다.")
        self.hp = min(self.max_hp, self.hp + 1)
        return f"와플을 먹어 하트를 회복했습니다! ({self.hp}/{self.max_hp})"

    def use_radio(self) -> dict:
        """무전기: 다음 갈림길의 위험도를 미리 보여준다 (소모)."""
        if not self.inventory.consume("radio"):
            raise ValueError("무전기가 없습니다.")
        return self.current_junction_options()

    # ---- movement ------------------------------------------------------
    def advance(self, direction: str) -> StepOutcome:
        if self.game_over or self.season_cleared:
            raise RuntimeError("Game has ended; start a new run.")
        junction = self.maze.junctions[self.position]
        if direction not in junction.options:
            raise ValueError(f"Invalid direction: {direction}")
        node_type = junction.options[direction]
        self._pending_node = node_type

        if node_type == NodeType.PATH:
            self._advance_position()
            return StepOutcome(node_type, "조용한 통로를 지나갑니다.")

        if node_type == NodeType.ITEM:
            return self._handle_item_node()

        if node_type == NodeType.EXIT:
            self._advance_position()
            cleared = self._mark_stage_cleared()
            return StepOutcome(node_type, "출구를 발견했습니다!", stage_cleared=cleared,
                                season_cleared=self.season_cleared)

        # ENCOUNTER / EVENT / BOSS all require the player to pick an action.
        villain = self.season["villain"]
        if node_type == NodeType.BOSS:
            intro = villain["boss_intro"]
        elif node_type == NodeType.EVENT:
            intro = villain.get("event_intro", villain["intro"])
        else:
            intro = villain["intro"]
        return StepOutcome(node_type, intro, requires="action_choice")

    def _advance_position(self) -> None:
        self.position += 1
        self._clear_pending()

    def _mark_stage_cleared(self) -> bool:
        if self.position < self.maze.length:
            return False
        self.cleared_stages.add(self.stage_id)
        if self.stage_id >= max(s["id"] for s in self.season["stages"]):
            self.season_cleared = True
        return True

    def advance_to_next_stage(self) -> bool:
        """Call after a stage_cleared outcome. Returns False if the season is done."""
        next_id = self.stage_id + 1
        if next_id > max(s["id"] for s in self.season["stages"]):
            return False
        self._start_stage(next_id)
        return True

    # ---- item nodes ------------------------------------------------
    def _draw_item(self) -> str:
        pool = self.season["item_pool"]
        return self._rng.choice(pool)

    def _handle_item_node(self) -> StepOutcome:
        if self.character.ability == "relentless":  # 조이스: 후보 2개 중 선택
            candidates = [self._draw_item(), self._draw_item()]
            self._pending_item_choice = candidates
            names = ", ".join(self.all_items[c].name for c in candidates)
            return StepOutcome(NodeType.ITEM, f"조이스가 집요하게 뒤져 두 가지를 찾아냈습니다: {names}",
                                requires="item_choice")
        item_id = self._draw_item()
        self.inventory.add(item_id)
        self._advance_position()
        return StepOutcome(NodeType.ITEM, f"{self.all_items[item_id].name}을(를) 획득했습니다!")

    def choose_item(self, item_id: str) -> StepOutcome:
        if not self._pending_item_choice or item_id not in self._pending_item_choice:
            raise ValueError("No such item pending.")
        self.inventory.add(item_id)
        self._advance_position()
        return StepOutcome(NodeType.ITEM, f"{self.all_items[item_id].name}을(를) 획득했습니다!")

    # ---- encounters (ENCOUNTER / BOSS / EVENT) ----------------------
    def usable_combat_items(self) -> list[str]:
        return [iid for iid, n in self.inventory.counts.items()
                if self.all_items[iid].effect in FIGHT_ITEM_EFFECTS]

    def start_quiz(self) -> tuple[str, list[str]]:
        quiz = self._rng.choice(self.season["quiz_bank"])
        options, correct = build_quiz_options(quiz["options"], quiz["answer_index"], self.character, self._rng)
        self._pending_quiz = {"correct": correct}
        return quiz["question"], options

    def start_preference(self) -> tuple[str, list[str]]:
        pref = self._rng.choice(self.season["preference_bank"])
        correct = pref["options"][pref["answer_index"]]
        self._pending_pref = {"correct": correct}
        return pref["prompt"], list(pref["options"])

    def resolve_fight(self, item_id: Optional[str] = None) -> StepOutcome:
        villain = self.season["villain"]
        base = villain["base_fight_success"]
        if self._pending_node == NodeType.BOSS:
            base = max(0.05, base - villain.get("boss_fight_penalty", 0))

        item_bonus = 0.0
        instant_win = False
        if item_id:
            if not self.inventory.consume(item_id):
                raise ValueError("Item not in inventory.")
            item = self.all_items[item_id]
            if item.effect == "instant_win_fight":
                instant_win = True
            elif item.effect == "fight_bonus":
                item_bonus = item.amount

        resolution = resolve_fight(self.character, self._rng, base, item_bonus, instant_win)
        return self._finish_encounter(resolution)

    def answer_quiz(self, chosen: str) -> StepOutcome:
        if not self._pending_quiz:
            raise RuntimeError("No quiz pending.")
        resolution = resolve_quiz(chosen, self._pending_quiz["correct"])
        return self._finish_encounter(resolution)

    def answer_preference(self, chosen: str) -> StepOutcome:
        if not self._pending_pref:
            raise RuntimeError("No preference check pending.")
        resolution = resolve_preference(chosen, self._pending_pref["correct"])
        return self._finish_encounter(resolution)

    def _finish_encounter(self, resolution: Resolution) -> StepOutcome:
        node_type = self._pending_node
        resolution = apply_leadership_retry(self.character, resolution)

        # EVENT nodes are lower-stakes: no HP cost, just flavor + always passable.
        if node_type == NodeType.EVENT:
            self._advance_position()
            return StepOutcome(node_type, resolution.message, success=resolution.success)

        if resolution.success:
            if node_type == NodeType.BOSS:
                self._advance_position()
                cleared = self._mark_stage_cleared()
                return StepOutcome(node_type, resolution.message, success=True, stage_cleared=cleared,
                                    season_cleared=self.season_cleared)
            self._advance_position()
            return StepOutcome(node_type, resolution.message, success=True)

        # Failure: HP cost. Regular encounters still let you stagger forward;
        # a BOSS is a fixed battle -- you stay and must try again.
        self.hp -= 1
        if self.hp <= 0:
            self.game_over = True
            return StepOutcome(node_type, resolution.message + " 하트가 모두 사라졌습니다... GAME OVER",
                                success=False, game_over=True)
        if node_type == NodeType.BOSS:
            self._clear_pending()
            return StepOutcome(node_type, resolution.message + " (보스전은 계속됩니다 — 다시 도전하세요)",
                                success=False)
        self._advance_position()
        return StepOutcome(node_type, resolution.message, success=False)

    # ---- game over / restart ----------------------------------------
    def restart_season(self, new_seed: Optional[int] = None) -> None:
        self.seed = new_seed if new_seed is not None else random.randrange(1_000_000_000)
        self.start_new_run(self.character.id, seed=self.seed)

    # ---- persistence --------------------------------------------------
    def to_state(self) -> dict:
        return {
            "character_id": self.character.id,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "inventory": self.inventory.to_dict(),
            "seed": self.seed,
            "stage_id": self.stage_id,
            "position": self.position,
            "cleared_stages": sorted(self.cleared_stages),
            "season_cleared": self.season_cleared,
            "ability_used": self.character.ability_used,
            "action_locked": self.character.action_locked,
        }

    @classmethod
    def from_state(cls, season_data: dict, state: dict) -> "GameEngine":
        engine = cls(season_data, seed=state["seed"])
        engine.character = get_character(state["character_id"])
        engine.character.ability_used = state.get("ability_used", False)
        engine.character.action_locked = state.get("action_locked", False)
        engine.hp = state["hp"]
        engine.max_hp = state["max_hp"]
        engine.inventory = Inventory.from_dict(state.get("inventory", {}))
        engine.stage_id = state["stage_id"]
        engine.cleared_stages = set(state.get("cleared_stages", []))
        engine.season_cleared = state.get("season_cleared", False)
        engine._rng = random.Random(f"{engine.seed}:runtime")
        stage = engine._stage_def(engine.stage_id)
        engine.maze = generate_maze(stage, engine.seed)
        engine.position = state["position"]
        return engine

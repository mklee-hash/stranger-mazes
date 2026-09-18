import random

from stranger_mazes.engine import content
from stranger_mazes.engine.game import GameEngine
from stranger_mazes.engine.maze import Junction, Maze, NodeType


class FixedRandom(random.Random):
    """A Random whose .random() always returns a fixed roll, so fight
    success/failure is deterministic in tests. .choice()/.shuffle() are left
    untouched (they use _randbelow, not random()), so quiz/item draws still
    work normally."""

    def __init__(self, fixed_value: float):
        super().__init__(0)
        self._fixed_value = fixed_value

    def random(self):
        return self._fixed_value


def _single_node_engine(character_id: str, node_type: NodeType, *, stage_id: int = 1) -> GameEngine:
    season = content.load_season(1)
    engine = GameEngine(season, seed=1)
    engine.start_new_run(character_id)
    engine.stage_id = stage_id
    engine.maze = Maze(seed=1, stage_id=stage_id, junctions=[
        Junction(0, {"좌": node_type, "직진": node_type, "우": node_type})
    ])
    engine.position = 0
    engine.character.reset_runtime_state()
    return engine


def test_hp_starts_at_character_base_hp():
    engine = _single_node_engine("mike", NodeType.PATH)
    assert engine.hp == engine.max_hp == 3

    hopper = _single_node_engine("hopper", NodeType.PATH)
    assert hopper.hp == hopper.max_hp == 4


def test_path_node_advances_without_damage():
    engine = _single_node_engine("mike", NodeType.PATH)
    outcome = engine.advance("좌")
    assert outcome.requires is None
    assert engine.position == 1
    assert engine.hp == engine.max_hp


def test_item_node_auto_pickup_for_most_characters():
    engine = _single_node_engine("mike", NodeType.ITEM)
    outcome = engine.advance("직진")
    assert outcome.requires is None
    assert sum(engine.inventory.counts.values()) == 1
    assert engine.position == 1


def test_joyce_item_node_offers_a_choice_between_two():
    engine = _single_node_engine("joyce", NodeType.ITEM)
    outcome = engine.advance("우")
    assert outcome.requires == "item_choice"
    candidates = engine.pending_item_choices
    assert len(candidates) == 2

    picked = candidates[0]
    outcome2 = engine.choose_item(picked)
    assert engine.inventory.counts.get(picked) == 1
    assert engine.position == 1
    assert outcome2.requires is None


def test_encounter_failure_costs_one_heart_but_still_advances():
    engine = _single_node_engine("lucas", NodeType.ENCOUNTER)  # marksman: +0.15, no retry ability
    engine._rng = FixedRandom(0.999)  # forces a miss regardless of bonus
    engine.advance("좌")
    result = engine.resolve_fight()
    assert result.success is False
    assert engine.hp == engine.max_hp - 1
    assert engine.position == 1  # regular encounters let you stagger onward


def test_encounter_success_costs_no_heart():
    engine = _single_node_engine("lucas", NodeType.ENCOUNTER)
    engine._rng = FixedRandom(0.0)  # always beats the success threshold
    engine.advance("좌")
    result = engine.resolve_fight()
    assert result.success is True
    assert engine.hp == engine.max_hp
    assert engine.position == 1


def test_waffle_heals_one_heart_and_is_consumed():
    engine = _single_node_engine("mike", NodeType.PATH)
    engine.hp = engine.max_hp - 1
    engine.inventory.add("waffle")
    engine.use_waffle()
    assert engine.hp == engine.max_hp
    assert engine.inventory.has("waffle") is False


def test_molotov_wins_a_fight_instantly_and_is_consumed():
    engine = _single_node_engine("mike", NodeType.ENCOUNTER)
    engine.inventory.add("molotov")
    engine._rng = FixedRandom(0.999)  # would normally fail
    engine.advance("좌")
    result = engine.resolve_fight(item_id="molotov")
    assert result.success is True
    assert engine.hp == engine.max_hp
    assert engine.inventory.has("molotov") is False


def test_el_psychic_strike_guarantees_first_win_then_locks_action():
    engine = _single_node_engine("el", NodeType.ENCOUNTER)
    engine._rng = FixedRandom(0.999)  # would normally fail
    engine.advance("좌")
    result = engine.resolve_fight()
    assert result.success is True
    assert engine.character.ability_used is True
    assert engine.character.action_locked is True
    assert engine.hp == engine.max_hp

    # Ability is one-time: the next encounter behaves like a normal fight.
    engine.maze = Maze(seed=1, stage_id=engine.stage_id, junctions=[
        Junction(0, {"좌": NodeType.ENCOUNTER, "직진": NodeType.ENCOUNTER, "우": NodeType.ENCOUNTER})
    ])
    engine.position = 0
    engine.advance("좌")
    result2 = engine.resolve_fight()
    assert result2.success is False
    assert engine.hp == engine.max_hp - 1


def test_hopper_fight_success_is_floored_at_80_percent():
    winner = _single_node_engine("hopper", NodeType.ENCOUNTER)
    winner._rng = FixedRandom(0.79)  # just under the 80% floor
    winner.advance("좌")
    assert winner.resolve_fight().success is True

    loser = _single_node_engine("hopper", NodeType.ENCOUNTER)
    loser._rng = FixedRandom(0.85)  # above the 80% floor
    loser.advance("좌")
    assert loser.resolve_fight().success is False


def test_mike_leadership_converts_first_failure_only():
    engine = _single_node_engine("mike", NodeType.ENCOUNTER)
    engine._rng = FixedRandom(0.99)  # would normally fail (base 50%)
    engine.advance("좌")
    result = engine.resolve_fight()
    assert result.success is True  # converted by leadership
    assert engine.character.ability_used is True
    assert engine.hp == engine.max_hp  # converted before HP was charged

    engine.maze = Maze(seed=1, stage_id=engine.stage_id, junctions=[
        Junction(0, {"좌": NodeType.ENCOUNTER, "직진": NodeType.ENCOUNTER, "우": NodeType.ENCOUNTER})
    ])
    engine.position = 0
    engine.advance("좌")
    result2 = engine.resolve_fight()
    assert result2.success is False  # already used this stage
    assert engine.hp == engine.max_hp - 1


def test_dustin_genius_reduces_quiz_to_two_options():
    dustin = _single_node_engine("dustin", NodeType.ENCOUNTER)
    dustin.advance("좌")
    _, options = dustin.start_quiz()
    assert len(options) == 2

    mike = _single_node_engine("mike", NodeType.ENCOUNTER)
    mike.advance("직진")
    _, options2 = mike.start_quiz()
    assert len(options2) == 4


def test_quiz_correct_and_incorrect_answers():
    correct_engine = _single_node_engine("lucas", NodeType.ENCOUNTER)
    correct_engine.advance("좌")
    _, options = correct_engine.start_quiz()
    correct = correct_engine._pending_quiz["correct"]
    result = correct_engine.answer_quiz(correct)
    assert result.success is True
    assert correct_engine.hp == correct_engine.max_hp

    wrong_engine = _single_node_engine("lucas", NodeType.ENCOUNTER)
    wrong_engine.advance("직진")
    _, options2 = wrong_engine.start_quiz()
    correct2 = wrong_engine._pending_quiz["correct"]
    wrong = next(o for o in options2 if o != correct2)
    result2 = wrong_engine.answer_quiz(wrong)
    assert result2.success is False
    assert wrong_engine.hp == wrong_engine.max_hp - 1


def test_event_node_never_costs_hp_but_still_advances():
    engine = _single_node_engine("lucas", NodeType.EVENT)
    engine.advance("좌")
    _, options = engine.start_preference()
    correct = engine._pending_pref["correct"]
    wrong = next(o for o in options if o != correct)
    result = engine.answer_preference(wrong)
    assert result.node_type == NodeType.EVENT
    assert result.success is False
    assert engine.hp == engine.max_hp
    assert engine.position == 1


def test_hp_reaching_zero_ends_the_run():
    engine = _single_node_engine("lucas", NodeType.ENCOUNTER)
    engine.hp = 1
    engine._rng = FixedRandom(0.999)
    engine.advance("좌")
    result = engine.resolve_fight()
    assert result.game_over is True
    assert engine.hp == 0
    assert engine.game_over is True


def test_restart_season_resets_hp_stage_and_position():
    engine = _single_node_engine("lucas", NodeType.ENCOUNTER)
    engine.hp = 0
    engine.game_over = True
    engine.stage_id = 3
    engine.restart_season(new_seed=555)
    assert engine.hp == engine.max_hp
    assert engine.game_over is False
    assert engine.stage_id == 1
    assert engine.position == 0


def test_boss_failure_holds_the_gate_but_success_clears_the_stage():
    season = content.load_season(1)
    boss_stage = next(s for s in season["stages"] if s.get("boss"))
    engine = _single_node_engine("joyce", NodeType.BOSS, stage_id=boss_stage["id"])

    engine._rng = FixedRandom(0.999)
    engine.advance("좌")
    result = engine.resolve_fight()
    assert result.success is False
    assert result.stage_cleared is False
    assert engine.position == 0  # boss gate does not let you slip past on a loss
    assert engine.hp == engine.max_hp - 1

    engine._rng = FixedRandom(0.0)
    engine.advance("직진")  # try the gate again
    result2 = engine.resolve_fight()
    assert result2.success is True
    assert result2.stage_cleared is True
    assert engine.position == 1


def test_save_state_roundtrip_restores_progress():
    engine = _single_node_engine("mike", NodeType.PATH)
    engine.inventory.add("waffle")
    engine.hp = 2
    state = engine.to_state()

    season = content.load_season(1)
    restored = GameEngine.from_state(season, state)
    assert restored.character.id == "mike"
    assert restored.hp == 2
    assert restored.inventory.has("waffle")
    assert restored.stage_id == engine.stage_id

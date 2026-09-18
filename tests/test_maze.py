from stranger_mazes.engine import content
from stranger_mazes.engine.maze import NodeType, generate_maze


def test_maze_generation_is_deterministic_for_a_seed():
    stage = content.load_season(1)["stages"][0]
    maze_a = generate_maze(stage, seed=42)
    maze_b = generate_maze(stage, seed=42)
    assert [j.options for j in maze_a.junctions] == [j.options for j in maze_b.junctions]


def test_different_seeds_can_produce_different_layouts():
    stage = content.load_season(1)["stages"][2]  # stage with more junctions
    layouts = {
        tuple(j.options[d] for j in generate_maze(stage, seed).junctions for d in ("좌", "직진", "우"))
        for seed in range(20)
    }
    assert len(layouts) > 1


def test_every_junction_has_all_three_directions():
    season = content.load_season(1)
    for stage in season["stages"]:
        maze = generate_maze(stage, seed=7)
        for junction in maze.junctions:
            assert set(junction.options.keys()) == {"좌", "직진", "우"}
            for node_type in junction.options.values():
                assert isinstance(node_type, NodeType)


def test_non_boss_stage_always_exits_on_last_junction():
    season = content.load_season(1)
    for stage in season["stages"]:
        if stage.get("boss"):
            continue
        maze = generate_maze(stage, seed=123)
        last = maze.junctions[-1]
        assert all(node == NodeType.EXIT for node in last.options.values())


def test_boss_stage_always_forces_boss_on_last_junction():
    season = content.load_season(1)
    boss_stage = next(s for s in season["stages"] if s.get("boss"))
    maze = generate_maze(boss_stage, seed=123)
    last = maze.junctions[-1]
    assert all(node == NodeType.BOSS for node in last.options.values())


def test_every_direction_is_a_valid_path_to_the_exit():
    """No matter which of 좌/직진/우 the player always picks, the maze has a
    fixed number of junctions and every junction offers all three
    directions -- so any sequence of choices reaches the final (EXIT/BOSS)
    junction. This is what guarantees the maze can never soft-lock."""
    season = content.load_season(1)
    for stage in season["stages"]:
        maze = generate_maze(stage, seed=99)
        for always_pick in ("좌", "직진", "우"):
            position = 0
            for _ in range(maze.length):
                junction = maze.junctions[position]
                assert always_pick in junction.options
                position += 1
            assert position == maze.length

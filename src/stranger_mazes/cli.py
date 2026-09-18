"""Thin text UI over GameEngine. No game rules live here -- only prompting
and printing, so this file is what gets replaced by a web/3D front-end later.
"""
from __future__ import annotations

from .engine import content, save
from .engine.game import GameEngine, StepOutcome
from .engine.maze import NodeType

NODE_LABELS = {
    NodeType.PATH: "조용한 길",
    NodeType.ITEM: "무언가 반짝임",
    NodeType.ENCOUNTER: "위험한 기척",
    NodeType.EVENT: "이상한 낌새",
    NodeType.BOSS: "강력한 기운",
    NodeType.EXIT: "출구",
}


def _prompt(prompt: str, options: list[str]) -> str:
    while True:
        print(prompt)
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        raw = input("> ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("올바른 번호를 입력해주세요.\n")


def _print_status(engine: GameEngine) -> None:
    hearts = "♥" * engine.hp + "♡" * (engine.max_hp - engine.hp)
    inv = ", ".join(f"{engine.all_items[i].name}x{n}" for i, n in engine.inventory.counts.items()) or "없음"
    print(f"\n[{engine.stage_name}] {engine.position + 1}/{engine.stage_length}  HP:{hearts}  아이템: {inv}")


def _handle_action_choice(engine: GameEngine) -> StepOutcome:
    action = _prompt("빌런과 마주쳤습니다! 어떻게 하시겠습니까?", ["싸움", "퀴즈 풀기", "취향 맞추기"])
    if action == "싸움":
        combat_items = engine.usable_combat_items()
        item_id = None
        if combat_items:
            choices = [engine.all_items[i].name for i in combat_items] + ["그냥 싸운다"]
            picked = _prompt("전투에 쓸 아이템이 있습니다. 사용하시겠습니까?", choices)
            if picked != "그냥 싸운다":
                item_id = combat_items[choices.index(picked)]
        return engine.resolve_fight(item_id)
    if action == "퀴즈 풀기":
        question, options = engine.start_quiz()
        print(f"\n💬 {question}")
        chosen = _prompt("정답을 고르세요.", options)
        return engine.answer_quiz(chosen)
    prompt_text, options = engine.start_preference()
    print(f"\n💬 {prompt_text}")
    chosen = _prompt("행동을 고르세요.", options)
    return engine.answer_preference(chosen)


def _login_or_guest() -> str | None:
    raw = input("로그인할 계정명을 입력하세요 (그냥 Enter = guest로 플레이): ").strip()
    return raw or None


def _select_character(engine: GameEngine) -> str:
    ids = engine.playable_character_ids
    labels = [f"{engine.all_characters[cid].name} — {engine.all_characters[cid].description}" for cid in ids]
    picked = _prompt("플레이할 캐릭터를 선택하세요.", labels)
    return ids[labels.index(picked)]


def _play_stage(engine: GameEngine, username: str | None) -> None:
    while not engine.game_over and not engine.season_cleared:
        _print_status(engine)
        options = engine.current_junction_options()
        directions = list(options.keys())

        # Junction-level item use (와플 / 무전기) before choosing direction.
        junction_items = [i for i in engine.inventory.counts if i in ("waffle", "radio")]
        if junction_items:
            menu = [f"{engine.all_items[i].name} 사용" for i in junction_items] + ["이동한다"]
            picked = _prompt("갈림길에 도착했습니다.", menu)
            if picked != "이동한다":
                item_id = junction_items[menu.index(picked)]
                if item_id == "waffle":
                    print(engine.use_waffle())
                else:
                    peek = engine.use_radio()
                    print("무전기로 살펴본 다음 갈림길:")
                    for d, nt in peek.items():
                        print(f"  {d}: {NODE_LABELS[nt]}")

        direction = _prompt("어느 방향으로 가시겠습니까?", directions)
        outcome = engine.advance(direction)
        print(outcome.message)

        if outcome.requires == "item_choice":
            candidates = engine.pending_item_choices
            names = [engine.all_items[c].name for c in candidates]
            picked = _prompt("어느 아이템을 챙기시겠습니까?", names)
            outcome = engine.choose_item(candidates[names.index(picked)])
            print(outcome.message)
        elif outcome.requires == "action_choice":
            outcome = _handle_action_choice(engine)
            print(outcome.message)

        if username and not outcome.game_over:
            save.write_save(username, engine.to_state())

        if outcome.game_over:
            print("\n💀 GAME OVER — 시즌 1단계부터 다시 시작합니다.")
            if username:
                save.delete_save(username)
            engine.restart_season()
            continue

        if outcome.stage_cleared:
            if outcome.season_cleared:
                print(f"\n🎉 STAGE {engine.stage_id} CLEAR! 시즌 1을 모두 클리어했습니다! 🎉")
                if username:
                    save.write_save(username, engine.to_state())
                break
            print(f"\n✅ STAGE {engine.stage_id} CLEAR!")
            engine.advance_to_next_stage()
            if username:
                save.write_save(username, engine.to_state())


def main() -> None:
    print("=" * 50)
    print(" 기묘한 미로 (Stranger Mazes) — 시즌 1 텍스트 시뮬레이션")
    print("=" * 50)

    season = content.load_season(1)
    username = _login_or_guest()

    engine: GameEngine
    if username and save.has_save(username):
        choice = _prompt(f"'{username}'님의 저장된 게임이 있습니다.", ["이어하기", "처음부터 하기"])
        if choice == "이어하기":
            state = save.load_save(username)
            engine = GameEngine.from_state(season, state)
            print(f"\n{engine.character.name}(으)로 {engine.stage_name}에서 이어합니다.")
        else:
            engine = GameEngine(season)
            engine.start_new_run(_select_character(engine))
            save.write_save(username, engine.to_state())
    else:
        if username is None:
            print("(guest로 플레이합니다 — 진행 상황은 저장되지 않습니다.)")
        engine = GameEngine(season)
        engine.start_new_run(_select_character(engine))
        if username:
            save.write_save(username, engine.to_state())

    _play_stage(engine, username)
    print("\n게임을 종료합니다. 즐거운 시간 되셨길 바랍니다!")


if __name__ == "__main__":
    main()

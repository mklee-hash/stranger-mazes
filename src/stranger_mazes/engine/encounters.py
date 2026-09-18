"""Resolves a villain encounter via one of: 싸움(fight) / 퀴즈(quiz) / 취향 맞추기(preference).

Character abilities hook in here rather than being special-cased in GameEngine,
so a new character only needs a new `ability` id handled in one place.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .characters import Character


@dataclass
class Resolution:
    success: bool
    message: str


def resolve_fight(
    character: Character,
    rng: random.Random,
    base_success: float,
    item_bonus: float = 0.0,
    instant_win: bool = False,
) -> Resolution:
    if instant_win:
        return Resolution(True, "화염병이 폭발하며 전투가 즉시 승리로 끝났습니다!")

    success_chance = base_success
    note = ""

    if character.ability == "toughness":  # 호퍼
        success_chance = max(success_chance, 0.8)
        note = " (호퍼의 완력으로 성공 확률 80% 고정)"

    if character.ability == "psychic_strike" and not character.ability_used:  # 엘
        character.ability_used = True
        character.action_locked = True
        return Resolution(
            True,
            f"{character.name}이(가) 초능력을 사용해 단숨에 제압합니다! "
            "(코피가 나며 다음 턴 행동에 제약이 걸립니다)",
        )

    if character.ability == "marksman":  # 루카스
        success_chance += 0.15
        note += " (루카스의 명사수 보너스 +15%)"

    success_chance = min(0.95, success_chance + item_bonus)
    success = rng.random() < success_chance
    msg = f"싸움 판정 성공 확률 {int(success_chance * 100)}%{note} → {'성공' if success else '실패'}"
    return Resolution(success, msg)


def build_quiz_options(
    options: list[str], answer_index: int, character: Character, rng: random.Random
) -> tuple[list[str], str]:
    """Returns (displayed_options, correct_answer_text)."""
    correct = options[answer_index]
    displayed = list(options)
    if character.ability == "genius":  # 더스틴: 4지선다 -> 2지선다
        wrong = [o for o in displayed if o != correct]
        rng.shuffle(wrong)
        displayed = [correct, wrong[0]]
        rng.shuffle(displayed)
    return displayed, correct


def resolve_quiz(chosen: str, correct: str) -> Resolution:
    success = chosen == correct
    msg = "정답입니다! 안전하게 다음 갈림길로 향합니다." if success else f"오답입니다. 정답은 '{correct}' 였습니다."
    return Resolution(success, msg)


def resolve_preference(chosen: str, correct: str) -> Resolution:
    success = chosen == correct
    msg = "빌런의 취향을 정확히 맞춰 전투 없이 지나갑니다." if success else "빌런의 심기를 건드렸습니다."
    return Resolution(success, msg)


def apply_leadership_retry(character: Character, resolution: Resolution) -> Resolution:
    """마이크: Stage당 1회, 실패를 자동 재도전(성공)으로 전환한다."""
    if character.ability == "leadership" and not resolution.success and not character.ability_used:
        character.ability_used = True
        return Resolution(
            True,
            resolution.message + " → 마이크가 팀을 재정비해 재도전, 결국 성공합니다!",
        )
    return resolution

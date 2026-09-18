"""Guest vs. login save behaviour (2차 작업 지시).

Guest(비로그인)로 플레이하면 저장되지 않는다 -- 즉, GameEngine이 guest 모드일 때는
이 모듈을 아예 호출하지 않는다 (game.py 참고). 로그인 유저는 Stage 클리어나
이벤트 결과가 나올 때마다 자동 저장되고, 재접속 시 이어하기/처음부터를 고를 수
있다. 저장 형식은 스펙 그대로 가벼운 JSON 파일 하나 (SQLite로 바꿔도 이 모듈의
공개 함수 시그니처만 유지하면 game.py는 수정할 필요가 없다).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

SAVE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "saves"

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_\-가-힣]")


def _save_path(username: str) -> Path:
    safe = _SAFE_NAME.sub("_", username).strip("_") or "player"
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    return SAVE_DIR / f"{safe}.json"


def has_save(username: str) -> bool:
    return _save_path(username).exists()


def load_save(username: str) -> Optional[dict]:
    path = _save_path(username)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_save(username: str, state: dict) -> None:
    path = _save_path(username)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def delete_save(username: str) -> None:
    path = _save_path(username)
    if path.exists():
        path.unlink()

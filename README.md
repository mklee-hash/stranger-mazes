# 기묘한 미로 (Stranger Mazes)

3D 1인칭 미로 탈출 + 턴제 인카운터(전투/퀴즈/취향 맞추기) RPG.
기획 원본: `../기묘한 미로 설계.pptx` (v1), `기묘한_미로_게임설계_v2.pptx` (v2, Codex 구현용 — 이 프로젝트가 따르는 스펙).

## 🔗 플레이하기

**https://mklee-hash.github.io/stranger-mazes/** — Claude 계정/링크 없이 누구나 바로 접속 가능
(GitHub Pages, `docs/index.html`을 서빙. `web/index.html`을 수정한 뒤 `docs/index.html`에도
복사하고 커밋·푸시해야 배포본에 반영된다 — Pages는 `main` 브랜치의 `/docs` 폴더를 그대로 서빙하며
별도 빌드 단계가 없다).

## 개발 순서 (설계 문서 기준)

1. ✅ **Python 게임 엔진** — 시즌1을 텍스트(CLI)로 완주 가능하게 구현
2. ✅ **웹 버튼 UI** — `web/index-2d.html` (Artifact로도 배포)
3. ✅ **3D 1인칭 미로 (Three.js)** — `web/index.html` (Artifact로 배포, 현재 단계)

핵심 원칙: **게임 규칙(GameEngine)과 화면(UI)을 분리**한다. 콘텐츠(캐릭터/아이템/빌런/퀴즈)는
`src/stranger_mazes/data/*.json`(Python 엔진 기준)에 데이터로 정의해 시즌/캐릭터/빌런을 코드 수정
없이 추가할 수 있게 한다. `web/`의 두 HTML은 이 JSON을 JS로 1:1 이식한 브라우저용 사본으로,
게임 규칙 자체는 세 구현 모두 동일하다.

### web/ — 브라우저 버전

- `index.html` — **3D 1인칭** 버전 (Three.js). 진짜 벽/갈림길이 있는 격자 미로(recursive
  backtracker로 생성, EXIT까지 항상 도달 가능)를 방향키/드래그로 걷고 돈다. 스페이스바로
  바닥의 아이템(와플/무전기/횃불/화염병/새총 — 각각 고유한 3D 모양)을 줍고, 데모고르곤을
  만나면 1·2·3(또는 스페이스바로 고르고 엔터)로 싸움/퀴즈/취향 맞추기를 고른다. 화면 우측
  상단에 미니맵(현재 위치+방향), 탈출 성공 시 이동 경로가 표시된 결과 화면이 뜬다. 이
  브라우저의 localStorage에 자동 저장(이어하기)된다.
- `index-2d.html` — 이전 단계인 2D 버튼 UI 버전 (참고/비교용으로 보관).
- 두 파일 모두 규칙 로직(`GameEngine`)은 완전히 동일한 코드이고, 화면(뷰) 레이어만 다르다 —
  슬라이드19의 "게임을 다시 만드는 것이 아니라 화면을 교체하는 것" 원칙 그대로.
- 저장은 아직 **이 브라우저 로컬(localStorage)** 한정이다. 2차 작업지시의 계정 로그인 기반
  저장까지 가려면 별도 백엔드/인증이 필요하다.

## 핵심 루프

탐험(Explore) → 판단(Decide) → 조우(Encounter) → 해결(Resolve: 전투/퀴즈/취향 맞추기) → 보상(Reward) → 진행(Progress)

## 폴더 구조

```
src/stranger_mazes/
  engine/
    maze.py        # 시드 기반 미로 생성 (EXIT까지 유효 경로 보장)
    characters.py  # CharacterData 로딩 및 능력 훅
    items.py       # 아이템 획득/보관/사용/소모 공통 인터페이스
    encounters.py  # 전투/퀴즈/취향 맞추기 판정 로직
    save.py        # guest(미저장) vs 로그인(JSON 자동 저장, 이어하기)
    game.py        # GameEngine — 위 모듈을 조합, UI에 상태/선택지만 노출
  data/
    characters.json
    items.json
    season1.json     # Stage 구성, 빌런, 퀴즈, 이벤트 대사
cli.py                # 텍스트 기반 UI (엔진 호출만, 규칙 로직 없음)
tests/                # 슬라이드20 "개발 완료 기준" 체크리스트 검증
saves/                # 로그인 유저별 JSON 세이브 파일
```

## 시즌 1 — 호킨스 연구소 & 뒤집힌 세계

| Stage | 내용 |
|---|---|
| 1 | 연구소 외곽 — 튜토리얼, 기본 갈림길, 데모고르곤 1회 |
| 2 | 연구소 내부 — 갈림길 증가, 아이템 사용 학습 |
| 3 | 지하 통로 — 위험 노드 증가, 숨겨진 아이템 |
| 4 | 뒤집힌 세계 입구 — 고위험 미로, 데모고르곤 강화 |
| 5 | 시즌 보스 구역 — 고정 보스 배틀 → 출구 |

캐릭터: 엘, 마이크, 호퍼, 조이스, 더스틴, 루카스 · 빌런: 데모고르곤

## 실행

```bash
pip install -e .
python -m stranger_mazes.cli
```

> 이 PC에는 원래 Python이 설치돼 있지 않았습니다 (winget으로 Python 3.12를 새로 설치함,
> `%LOCALAPPDATA%\Programs\Python\Python312`). 새 터미널을 열면 PATH에 잡히지만, 지금 세션에서
> 바로 쓰려면 `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m stranger_mazes.cli`
> 처럼 전체 경로로 실행하세요.

## 테스트

```bash
pip install pytest
pytest
```

29개 테스트 모두 통과 확인 완료 (미로 생성/결정성/유효 경로, HP·아이템·캐릭터 능력, 세이브/로드,
게임오버·보스전 재도전 로직 등).

## 개발 완료 기준 (시즌 1)

- [x] 캐릭터를 선택하고 Stage를 시작할 수 있다.
- [x] 매 플레이마다 유효한 미로가 생성된다 (seed 기반, EXIT 도달 보장).
- [x] 갈림길에서 선택하여 이동할 수 있다.
- [x] 데모고르곤을 만날 수 있다.
- [x] 전투/퀴즈/취향 맞추기 중 하나로 해결할 수 있다.
- [x] 실패하면 HP가 감소한다.
- [x] 와플 등 아이템을 획득/사용할 수 있다.
- [x] 캐릭터 고유 능력이 실제 플레이에 영향을 준다.
- [x] HP 0이면 Game Over, 출구 도달 시 Clear가 된다.
- [x] 최소 자동 테스트로 핵심 규칙이 검증된다.
- [x] 이후 웹/3D UI로 확장 가능한 구조다 (엔진/UI 분리).
- [x] 로그인 여부에 따른 저장/이어하기 (2차 작업 지시).

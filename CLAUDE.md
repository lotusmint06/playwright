# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 구조

```
project/
├── conftest.py          # 브라우저 fixture (function/session), 환경 설정, Teams webhook
├── env.json             # QA/Prod × PC/Mobile 환경별 URL
├── locators.json        # 페이지별 selector 중앙 관리
├── validate_locators.py # locators.json 정합성 검증
├── self_healing.py      # OpenAI(gpt-4o-mini) 기반 self-healing
├── pytest.ini           # 기본 pytest 옵션
├── requirements.txt
├── tests/               # pytest 로직만 작성 (Playwright 문법 사용 금지)
└── scripts/             # Playwright 액션 담당 (BasePage 상속)
    └── base_page.py     # 공통 액션 + self-healing 연동
```

## 실행 명령어

```bash
# 설치
pip install -r requirements.txt
playwright install chromium

# 테스트 실행
pytest tests/                                  # 기본 (QA, PC)
pytest tests/ --env=prod --platform=mo         # 환경/플랫폼 지정
pytest tests/ -n auto                          # 병렬 실행 (xdist)
pytest tests/test_login.py                     # 단일 파일
pytest tests/ -k "test_login"                  # 특정 테스트

# locator 검증
python validate_locators.py
```

## 설계 원칙

- **tests/**: pytest assertion만 작성. `expect()`, `assert`만 사용
- **scripts/**: Playwright 액션 담당. `BasePage`를 상속해 Page Object 작성
- **locators.json**: selector를 코드와 분리. 동적 값은 `{value}` 플레이스홀더 사용
- **self-healing**: `OPENAI_API_KEY` 있을 때만 활성화. healing 성공 시 `healed: true` 플래그 → PR 전 수동 검토 필요

## locators.json 구조

```json
{
  "section": {
    "element_key": {
      "primary": "css=#id",
      "previous": null,
      "healed": false
    }
  }
}
```

동적 텍스트: `"primary": "text={value}"` → `click("section", "key", value="로그인")`

## fixture scope

- `page` (function scope): 기본. xdist 병렬 실행 시 사용
- `session_page` (session scope): 로그인 상태 유지가 필요한 테스트에서 선택

## 환경변수

```bash
export OPENAI_API_KEY="sk-..."     # self-healing 활성화
export TEAMS_WEBHOOK_URL="https://..."  # 테스트 결과 Teams 전송
```

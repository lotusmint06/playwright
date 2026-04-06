# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 구조

```
project/
├── conftest.py          # 공통 hook: 스크린샷, Teams webhook, locator 검증, pytest 옵션
├── env.json             # QA/Prod × PC/Mobile/Android/iOS 환경별 설정
├── locators.json        # 웹 페이지별 selector 중앙 관리
├── locators_app.json    # 앱 selector 중앙 관리 (android/ios 분기)
├── validate_locators.py # locators.json 정합성 검증
├── self_healing.py      # OpenAI(gpt-4o-mini) 기반 웹 self-healing
├── app_healing.py       # OpenAI(gpt-4o-mini) 기반 앱 self-healing
├── pytest.ini           # 기본 pytest 옵션
├── requirements.txt
├── tests/               # 웹 테스트 — pytest assertion만 작성 (Playwright 문법 사용 금지)
│   └── conftest.py      # Playwright fixture: page (function), session_page (session)
├── tests_app/           # 앱 테스트 — pytest assertion만 작성
│   └── conftest.py      # Appium fixture: app_driver (function)
└── scripts/             # Playwright 액션 담당 (BasePage 상속)
    ├── base_page.py     # 웹 공통 액션 + self-healing 연동
    └── base_app_page.py # 앱 공통 액션 + app_healing 연동
```

## 실행 명령어

```bash
# 설치
pip install -r requirements.txt
playwright install chromium

# 웹 테스트 실행
pytest tests/                                  # 기본 (QA, PC)
pytest tests/ --env=prod --platform=mo         # 환경/플랫폼 지정
pytest tests/ -n auto                          # 병렬 실행 (xdist)
pytest tests/test_login.py                     # 단일 파일
pytest tests/ -k "test_login"                  # 특정 테스트

# 앱 테스트 실행
pytest tests_app/                              # 기본 (QA, Android)
pytest tests_app/ --app-os=ios --env=prod      # iOS / Prod

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

- **루트 conftest.py**: 공통 hook (실패 스크린샷, Teams webhook, locator 검증, 옵션 정의)
- **tests/conftest.py**: `page` (function scope, 기본), `session_page` (session scope, 로그인 유지) — Playwright 전용
- **tests_app/conftest.py**: `app_driver` (function scope) — Appium 전용

## 환경변수

```bash
export OPENAI_API_KEY="sk-..."     # self-healing 활성화
export TEAMS_WEBHOOK_URL="https://..."  # 테스트 결과 Teams 전송
```

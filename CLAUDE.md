# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 구조

```
project/
├── conftest.py              # 공통 hook: 스크린샷, Teams webhook, locator 검증, pytest 옵션
├── env.json                 # QA/Prod × PC/Mobile/Android/iOS 환경별 설정
├── locators.json            # 웹 selector 중앙 관리 (primary/fallback/healed)
├── app_locators.json        # 앱 selector 중앙 관리 (primary/fallback/healed)
├── validate_locators.py     # locators.json 정합성 검증
├── self_healing.py          # OpenAI(gpt-4o-mini) 기반 웹 self-healing (HTML)
├── app_self_healing.py      # OpenAI(gpt-4o-mini) 기반 앱 self-healing (XML)
├── appium.config.json       # Appium 서버 설정
├── pytest.ini               # 기본 pytest 옵션
├── requirements.txt
├── tests/                   # 웹 테스트 — pytest assertion만 작성 (Playwright 문법 사용 금지)
│   └── conftest.py          # Playwright fixture: page (function), session_page (session)
├── tests_app/               # 앱 테스트 — pytest assertion만 작성
│   ├── conftest.py          # Appium fixture: 앱 종료/실행, 스플래시 대기, app_driver
│   ├── test_connection.py   # 디바이스 연결 및 앱 실행 확인 테스트
│   └── test_main.py         # 앱 메인화면 테스트
├── scripts/                 # 웹 Page Object (BasePage 상속)
│   ├── base_page.py         # 웹 공통 액션 + self-healing 연동
│   └── login_page.py
├── scripts_app/             # 앱 Page Object (BaseAppPage 상속)
│   ├── base_app_page.py     # Appium 공통 액션 + app-healing 연동 + stale retry
│   └── main_page.py         # 메인화면 Page Object
├── docs/                    # 설계 문서
│   ├── dom_context_optimization.md  # Self-Healing DOM 컨텍스트 최적화 ✅
│   └── appium_setup.md              # Appium 구현 가이드
└── tools/                   # 개발/검증 도구 (pytest 수집 대상 아님)
    └── check_context.py     # DOM 컨텍스트 추출 및 OpenAI 후보 품질 검증
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
pytest tests_app/test_connection.py --app-os=android -v -s  # 연결 확인

# locator 검증
python validate_locators.py

# Appium 서버 실행
appium --config appium.config.json
```

## 설계 원칙

- **tests/**: pytest assertion만 작성. `expect()`, `assert`만 사용
- **tests_app/**: pytest assertion만 작성. Appium 문법 직접 사용 금지
- **scripts/**: Playwright 액션 담당. `BasePage`를 상속해 Page Object 작성
- **scripts_app/**: Appium 액션 담당. `BaseAppPage`를 상속해 Page Object 작성
- **locators.json**: 웹 selector를 코드와 분리. 동적 값은 `{value}` 플레이스홀더 사용
- **app_locators.json**: 앱 selector를 코드와 분리. `accessibility_id:` / `uiautomator:` / `xpath:` / `id:` 접두사 사용
- **self-healing**: `OPENAI_API_KEY` 있을 때만 활성화. healing 성공 시 `healed: true` 플래그 → PR 전 수동 검토 필요

## locators.json 구조 (웹)

```json
{
  "section": {
    "element_key": {
      "primary": "css=#id",
      "fallback": ["role=button[name='텍스트']"],
      "previous": null,
      "healed": false
    }
  }
}
```

동적 텍스트: `"primary": "text={value}"` → `click("section", "key", value="로그인")`

## app_locators.json 구조 (앱)

```json
{
  "section": {
    "element_key": {
      "primary": "accessibility_id:요소명",
      "fallback": [
        "uiautomator:new UiSelector().description(\"요소명\")",
        "xpath://android.widget.Button[@content-desc='요소명']"
      ],
      "previous": null,
      "healed": false
    }
  }
}
```

selector 접두사: `accessibility_id:` / `uiautomator:` / `id:` / `xpath:`

## fixture scope

- **루트 conftest.py**: 공통 hook (실패 스크린샷, Teams webhook, locator 검증, 옵션 정의)
- **tests/conftest.py**: `page` (function scope, 기본), `session_page` (session scope, 로그인 유지) — Playwright 전용
- **tests_app/conftest.py**: `app_driver` (function scope) — Appium 전용. 앱 상태 확인 → 종료 → 실행 → 스플래시 대기 후 yield

## 환경변수

```bash
export OPENAI_API_KEY="sk-..."          # self-healing 활성화 (웹/앱 공통)
export TEAMS_WEBHOOK_URL="https://..."  # 테스트 결과 Teams 전송

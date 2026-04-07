# E2E Test Automation Framework

Python 기반 웹 + 앱 E2E 테스트 자동화 프레임워크입니다.  
Playwright(웹)와 Appium(앱)을 통합하고, OpenAI 기반 Self-Healing Locator를 구현했습니다.

---

## 기술 스택

| 구분 | 기술 |
|---|---|
| 웹 테스트 | Python · Playwright · pytest |
| 앱 테스트 | Appium · UiAutomator2 · XCUITest |
| Self-Healing | OpenAI gpt-4o-mini |
| 리포트 | pytest-html · Allure · MS Teams webhook |

---

## 핵심 특징

**1. Self-Healing Locator**  
selector가 깨지면 fallback으로 요소를 확보한 뒤, OpenAI가 새 primary selector를 자동 제안·갱신합니다.  
DOM 컨텍스트 최적화로 토큰 사용량을 기존 대비 72% 절감했습니다. → [상세](docs/dom_context_optimization.md)

**2. 웹 + 앱 통합 구조**  
Playwright(웹)와 Appium(Android/iOS) 모두 동일한 Page Object 패턴으로 관리합니다.  
테스트 코드(`tests/`, `tests_app/`)에는 프레임워크 문법을 직접 사용하지 않고 `assert`만 작성합니다.

**3. API 기반 테스트 데이터**  
Gateway API 응답에서 카테고리 목록을 동적으로 조회해 locator value와 assert 인자로 활용합니다.  
하드코딩 없이 앱 변경에 자동 대응합니다.

**4. Locator 중앙 관리**  
모든 selector를 `locators.json` / `app_locators.json`에서 관리합니다.  
테스트 시작 시 정합성을 자동 검증하고, healing된 항목은 `healed: true` 플래그로 추적합니다.

**5. Locator 사전 생성 도구**  
테스트 실패를 기다리지 않고, URL과 요소 설명만으로 selector를 사전에 생성해 `locators.json`에 자동 등록합니다. (웹 전용)

```bash
python tools/generate_locator.py \
    --url https://example.com/login \
    --section login --key email_input \
    --description "이메일 입력 필드"
```

---

## 프로젝트 구조

```
├── conftest.py              # 공통 hook (스크린샷, Teams webhook, locator 검증)
├── locators.json             # 웹 selector 중앙 관리
├── app_locators.json         # 앱 selector 중앙 관리
├── self_healing.py           # 웹 self-healing (OpenAI)
├── app_self_healing.py       # 앱 self-healing (OpenAI)
├── tests/                    # 웹 테스트 (assert만 작성)
│   ├── test_home.py
│   └── test_login.py
├── tests_app/                # 앱 테스트 (assert만 작성)
│   ├── test_connection.py
│   ├── test_main.py
│   └── test_categories.py
├── scripts/                  # 웹 Page Object (Playwright)
│   ├── base_page.py
│   ├── home_page.py
│   └── login_page.py
├── scripts_app/              # 앱 Page Object (Appium)
│   ├── base_app_page.py
│   ├── main_page.py
│   └── food_list_page.py
└── tools/                    # 개발·검증 도구
    ├── generate_locator.py   # URL → selector 사전 생성
    ├── api_client.py         # Gateway API 클라이언트
    └── check_context.py      # DOM 컨텍스트 검증
```

---

## 빠른 시작

```bash
# 설치
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 환경변수 설정
cp .env.example .env

# 웹 테스트
pytest tests/

# 앱 테스트 (Appium 서버 실행 후)
pytest tests_app/ --app-os=android
```

| 옵션 | 값 | 기본값 |
|---|---|---|
| `--env` | `qa` \| `prod` | `qa` |
| `--platform` | `pc` \| `mo` | `pc` |
| `--app-os` | `android` \| `ios` | `android` |

---

## 상세 문서

- [아키텍처 · 흐름도 · 설계 원칙](docs/details.md)
- [Self-Healing DOM 최적화](docs/dom_context_optimization.md)
- [Appium 설정 가이드](docs/appium_setup.md)

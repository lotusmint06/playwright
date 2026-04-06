# Appium 확장 준비 가이드

현재 Playwright 프레임워크(locators.json + primary/fallback + AI healing)를
Appium 모바일 테스트로 확장하기 위한 코드 및 설정 준비 사항.

---

## 목차

1. [설치 과정](#1-설치-과정)
2. [환경 요구사항 요약](#2-환경-요구사항-요약)
3. [프로젝트 구조 변경안](#3-프로젝트-구조-변경안)
4. [locators.json 구조 변경](#4-locatorsjson-구조-변경)
5. [BaseAppPage 코드](#5-baseapppage-코드)
6. [app_healing.py 코드](#6-app_healingpy-코드)
7. [conftest.py Appium fixture](#7-conftestpy-appium-fixture)
8. [locators_app.json 예시](#8-locators_appjson-예시)
9. [테스트 코드 예시](#9-테스트-코드-예시)
10. [CI 설정 고려사항](#10-ci-설정-고려사항)
11. [현재 코드와의 차이 요약](#11-현재-코드와의-차이-요약)

---

## 1. 설치 과정

### 1-1. Node.js 설치 (Appium 서버 의존성)

```bash
# macOS — Homebrew
brew install node

# 버전 확인 (Node 18+ 권장)
node --version
npm --version
```

### 1-2. Appium 서버 설치

```bash
npm install -g appium

# 설치 확인
appium --version
```

### 1-3. Appium 드라이버 설치

```bash
# Android
appium driver install uiautomator2

# iOS (macOS 전용)
appium driver install xcuitest

# 설치된 드라이버 목록 확인
appium driver list
```

### 1-4. JDK 설치 (Android 필수)

```bash
# macOS
brew install openjdk@17

# 환경변수 등록 (~/.zshrc에 추가)
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH=$JAVA_HOME/bin:$PATH

source ~/.zshrc

# 확인
java -version
```

### 1-5. Android SDK 설치

**방법 A — Android Studio (권장)**
1. Android Studio 설치
2. SDK Manager → `Android SDK Platform-Tools` 설치 확인
3. 환경변수 등록:

```bash
# ~/.zshrc에 추가
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$ANDROID_HOME/platform-tools:$PATH
export PATH=$ANDROID_HOME/emulator:$PATH
export PATH=$ANDROID_HOME/tools/bin:$PATH

source ~/.zshrc

# 확인
adb --version
```

**방법 B — Android Studio 없이 (command-line tools만)**
```bash
brew install --cask android-platform-tools
```

### 1-6. Xcode 설치 (iOS, macOS 전용)

```bash
# App Store에서 Xcode 설치 후 커맨드라인 도구 설치
xcode-select --install

# 라이선스 동의
sudo xcodebuild -license accept

# 확인
xcodebuild -version
```

### 1-7. Python 패키지 설치

```bash
pip install Appium-Python-Client==3.1.1
pip install selenium==4.21.0
```

`requirements.txt`에 추가:
```
Appium-Python-Client==3.1.1
selenium==4.21.0
```

### 1-8. 설치 환경 진단 — appium-doctor

```bash
npm install -g @appium/doctor

# Android 진단
appium-doctor --android

# iOS 진단
appium-doctor --ios
```

출력 예시:
```
✔ Node.js is installed at /usr/local/bin/node
✔ ANDROID_HOME is set
✔ JAVA_HOME is set
✔ adb exists at /Users/.../platform-tools/adb
✘ opencv4nodejs cannot be found  ← 이미지 비교 기능 미사용 시 무시 가능
```

핵심 항목(`ANDROID_HOME`, `JAVA_HOME`, `adb`)만 `✔`이면 기본 테스트 실행 가능.

### 1-9. 에뮬레이터 생성 (Android)

```bash
# Android Studio의 AVD Manager 사용 권장 (GUI)
# 또는 커맨드라인:
avdmanager create avd -n "Pixel_7_API_34" -k "system-images;android-34;google_apis;x86_64"

# 에뮬레이터 실행
emulator -avd Pixel_7_API_34 &

# 연결 확인
adb devices
# 출력: emulator-5554  device
```

### 1-10. Appium 서버 실행

```bash
# 기본 실행
appium --port 4723

# 로그 파일 저장
appium --port 4723 --log appium.log

# 백그라운드 실행
appium --port 4723 &
```

### 1-11. 연결 검증

에뮬레이터와 Appium 서버 모두 실행 후 확인:

```python
# verify_appium.py
from appium import webdriver
from appium.options.android import UiAutomator2Options

options = UiAutomator2Options()
options.platform_name = "Android"
options.device_name = "emulator-5554"
options.app_package = "com.android.settings"  # 기본 앱으로 연결 테스트
options.app_activity = ".Settings"
options.no_reset = True

try:
    driver = webdriver.Remote("http://localhost:4723", options=options)
    print("연결 성공:", driver.session_id)
    driver.quit()
except Exception as e:
    print("연결 실패:", e)
```

```bash
python verify_appium.py
# 연결 성공: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## 2. 환경 요구사항 요약

| 항목 | Android | iOS |
|---|---|---|
| OS | Windows / macOS / Linux | macOS 전용 |
| Node.js | 18+ | 18+ |
| JDK | 17+ | 불필요 |
| Android SDK + adb | 필수 | 불필요 |
| Xcode | 불필요 | 15+ |
| Appium 서버 | 2.x | 2.x |
| Appium 드라이버 | uiautomator2 | xcuitest |
| Python 패키지 | Appium-Python-Client 3.x | Appium-Python-Client 3.x |
| 실기기 테스트 추가 | USB 디버깅 활성화 | Apple 개발자 계정 + WebDriverAgent 빌드 |

---

## 3. 프로젝트 구조 변경안

```
project/
├── conftest.py              # 기존 Playwright fixture 유지
├── conftest_app.py          # Appium driver fixture (신규)
├── locators.json            # 웹 전용 (기존 유지)
├── locators_app.json        # 앱 전용 (신규) — android/ios 분기
├── self_healing.py          # 웹 self-healing (기존 유지)
├── app_healing.py           # 앱 self-healing (신규)
├── scripts/
│   ├── base_page.py         # Playwright 기반 (기존 유지)
│   └── base_app_page.py     # Appium 기반 (신규)
├── scripts_app/             # 앱 Page Object
│   └── login_app_page.py
└── tests_app/               # 앱 테스트
    └── test_login_app.py
```

> **분리 이유**: 웹/앱 코드가 섞이면 fixture 충돌 위험 있음. 별도 디렉터리로 유지하되 locators.json 구조와 healing 로직은 최대한 재사용.

---

## 4. locators.json 구조 변경

### 기존 웹 구조 (변경 없음)
```json
{
  "login": {
    "email_input": {
      "primary": "#input01",
      "fallback": ["role=textbox[name='아이디(이메일계정)']"],
      "healed": false
    }
  }
}
```

### 앱 전용 구조 (locators_app.json)
플랫폼 분기를 최상위 레벨로 두지 않고 요소별로 분기:
```json
{
  "login": {
    "email_input": {
      "android": {
        "primary": "accessibility id=email_input",
        "fallback": [
          "id=com.example.app:id/email_input",
          "//android.widget.EditText[@hint='이메일을 입력하세요']"
        ],
        "healed": false
      },
      "ios": {
        "primary": "accessibility id=email_input",
        "fallback": [
          "-ios predicate string:type == 'XCUIElementTypeTextField' AND value == '이메일을 입력하세요'"
        ],
        "healed": false
      }
    },
    "submit_btn": {
      "android": {
        "primary": "accessibility id=login_button",
        "fallback": [
          "id=com.example.app:id/btn_login",
          "//android.widget.Button[@text='로그인']"
        ],
        "healed": false
      },
      "ios": {
        "primary": "accessibility id=login_button",
        "fallback": [
          "-ios predicate string:type == 'XCUIElementTypeButton' AND label == '로그인'"
        ],
        "healed": false
      }
    }
  }
}
```

### locator 전략 우선순위

| 우선순위 | Playwright (웹) | Android (UIAutomator2) | iOS (XCUITest) |
|---|---|---|---|
| 1순위 | `#id` | `accessibility id` | `accessibility id` |
| 2순위 | `role=button[name=...]` | `id` (resource-id) | `-ios predicate string` |
| 3순위 | `.static-class` | `//android.widget.*[@text='...']` | `//XCUIElementTypeButton[@label='...']` |
| 금지 | `data-v-*` 해시 속성 | 인덱스 기반 xpath `//LinearLayout[2]` | 인덱스 기반 xpath `//XCUIElementTypeCell[3]` |

---

## 5. BaseAppPage 코드

`scripts/base_app_page.py` — `BasePage`와 구조 동일, Appium driver 대응

```python
"""
BaseAppPage — Appium 기반 Page Object의 부모 클래스

탐색 순서:
1. platform(android/ios)에 맞는 primary selector 시도
2. 실패 시 fallback 순차 시도
3. fallback 성공 → AI로 새 primary 제안 → locators_app.json 업데이트 (healed: true)
4. 모두 실패 → Exception
"""

import json
import os
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


LOCATOR_FILE = "locators_app.json"
DEFAULT_TIMEOUT = 5  # 초


def _parse_selector(selector: str):
    """
    selector 문자열을 (AppiumBy, value) 튜플로 변환.

    지원 형식:
      "accessibility id=login_button"
      "id=com.example.app:id/btn_login"
      "//android.widget.Button[@text='로그인']"  (xpath)
      "-ios predicate string:..."
      "-android uiautomator:..."
    """
    if selector.startswith("accessibility id="):
        return AppiumBy.ACCESSIBILITY_ID, selector[len("accessibility id="):]
    if selector.startswith("id="):
        return AppiumBy.ID, selector[len("id="):]
    if selector.startswith("//") or selector.startswith("(//"):
        return AppiumBy.XPATH, selector
    if selector.startswith("-ios predicate string:"):
        return AppiumBy.IOS_PREDICATE, selector[len("-ios predicate string:"):]
    if selector.startswith("-android uiautomator:"):
        return AppiumBy.ANDROID_UIAUTOMATOR, selector[len("-android uiautomator:"):]
    # 기본값: accessibility id
    return AppiumBy.ACCESSIBILITY_ID, selector


class BaseAppPage:
    def __init__(self, driver, platform: str):
        """
        Args:
            driver: Appium WebDriver 인스턴스
            platform: "android" 또는 "ios"
        """
        self.driver = driver
        self.platform = platform.lower()
        self._load_locators()

    def _load_locators(self):
        with open(LOCATOR_FILE, encoding="utf-8") as f:
            self.locators = json.load(f)

    def _reload_locators(self):
        self._load_locators()
        print("[Locator] locators_app.json 리로드 완료")

    def _find_element(self, selector: str, timeout: int = DEFAULT_TIMEOUT):
        by, value = _parse_selector(selector)
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def get_locator(self, section: str, key: str):
        """
        플랫폼에 맞는 primary → fallback 순서로 요소 탐색.
        fallback 성공 시 AI healing 시도.
        """
        platform_entry = self.locators[section][key][self.platform]
        primary = platform_entry["primary"]
        fallbacks = platform_entry.get("fallback") or []
        if isinstance(fallbacks, str):
            fallbacks = [fallbacks]

        # 1. primary 시도
        try:
            element = self._find_element(primary)
            print(f"[Locator] {section}.{key}: primary 성공 → '{primary}'")
            return element
        except TimeoutException:
            print(f"[Locator] {section}.{key}: primary 실패 → '{primary}'")

        # 2. fallback 시도
        for fb in fallbacks:
            try:
                element = self._find_element(fb, timeout=3)
                print(f"[Locator] {section}.{key}: fallback 성공 → '{fb}'")
            except TimeoutException:
                print(f"[Locator] {section}.{key}: fallback 실패 → '{fb}'")
                continue

            # 3. AI healing (OPENAI_API_KEY 있을 때만)
            if not os.getenv("OPENAI_API_KEY"):
                print(f"[Locator] {section}.{key}: OPENAI_API_KEY 없음 → self-healing 건너뜀")
            else:
                try:
                    from app_healing import try_heal_primary_app
                    healed = try_heal_primary_app(self.driver, self.platform, section, key, primary, fb)
                    if healed:
                        self._reload_locators()
                except Exception as heal_e:
                    print(f"[Locator] {section}.{key}: self-healing 실패 / {heal_e}")

            return element

        raise Exception(f"[{section}.{key}] {self.platform}: primary, fallback 모두 실패")

    # ── 공통 액션 ──────────────────────────────────────────────────────────

    def tap(self, section: str, key: str):
        """요소 탭 (웹의 click에 해당)"""
        self.get_locator(section, key).click()

    def fill(self, section: str, key: str, text: str):
        """텍스트 입력"""
        element = self.get_locator(section, key)
        element.clear()
        element.send_keys(text)

    def get_text(self, section: str, key: str) -> str:
        return self.get_locator(section, key).text

    def is_visible(self, section: str, key: str) -> bool:
        """
        BasePage와 달리 get_locator()를 통해 fallback까지 고려.
        요소가 없으면 False 반환 (Exception 발생하지 않음).
        """
        try:
            element = self.get_locator(section, key)
            return element.is_displayed()
        except Exception:
            return False

    def swipe_up(self, duration_ms: int = 800):
        """화면 위로 스와이프 (스크롤)"""
        size = self.driver.get_window_size()
        start_x = size["width"] // 2
        start_y = int(size["height"] * 0.7)
        end_y = int(size["height"] * 0.3)
        self.driver.swipe(start_x, start_y, start_x, end_y, duration_ms)

    def hide_keyboard(self):
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass  # 키보드가 없으면 무시
```

---

## 6. app_healing.py 코드

`app_healing.py` — `self_healing.py`의 Appium 버전.
`page.evaluate(JS)` 대신 `driver.page_source` (XML) 사용.

```python
"""
Appium 기반 Self-Healing Locator

driver.page_source(XML)를 분석해 새 selector를 제안하고
locators_app.json을 자동 업데이트합니다.

웹과 차이점:
- DOM(HTML) 대신 page_source(XML) 사용
- Playwright selector 대신 Appium selector 문법 사용
- 플랫폼(android/ios)별 selector 전략 분리
"""

import json
import os
from openai import OpenAI

HEAL_COUNT_FILE = ".heal_count_app.json"
LOCATOR_FILE = "locators_app.json"
MAX_HEAL_COUNT = 3

client = OpenAI()


def _load_heal_counts() -> dict:
    if not os.path.exists(HEAL_COUNT_FILE):
        return {}
    with open(HEAL_COUNT_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_heal_counts(counts: dict):
    with open(HEAL_COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f, ensure_ascii=False, indent=2)


def _get_page_source(driver, max_chars: int = 6000) -> str:
    """
    Appium page_source는 XML 형식.
    웹 DOM보다 훨씬 크므로 컷 기준 강화.
    """
    try:
        source = driver.page_source
        return source[:max_chars]
    except Exception as e:
        print(f"[App-Healing] page_source 추출 실패: {e}")
        return ""


def _get_android_prompt_rules() -> str:
    return (
        "Android UIAutomator2 selector를 제안해주세요.\n"
        "우선순위:\n"
        "  1순위: accessibility id=<value> (content-desc 또는 accessibility-id)\n"
        "  2순위: id=<package>:id/<resource-id>\n"
        "  3순위: //android.widget.*[@text='...' 또는 @content-desc='...']\n"
        "절대 금지: 인덱스 기반 xpath (//LinearLayout[2], //android.view.View[3] 등)\n"
        "응답 형식: {\"selectors\": [\"accessibility id=...\", \"id=...\", \"//...\"]}"
    )


def _get_ios_prompt_rules() -> str:
    return (
        "iOS XCUITest selector를 제안해주세요.\n"
        "우선순위:\n"
        "  1순위: accessibility id=<value> (accessibilityIdentifier)\n"
        "  2순위: -ios predicate string:type == 'XCUIElementType...' AND label == '...'\n"
        "  3순위: //XCUIElementTypeButton[@label='...']\n"
        "절대 금지: 인덱스 기반 xpath (//XCUIElementTypeCell[3] 등)\n"
        "응답 형식: {\"selectors\": [\"accessibility id=...\", \"-ios predicate string:...\", \"//...\"]}"
    )


def heal_locator_app(driver, platform: str, section: str, key: str, failed_selector: str) -> list[str]:
    """page_source XML을 분석해 새 selector 후보 반환"""
    page_source = _get_page_source(driver)
    rules = _get_android_prompt_rules() if platform == "android" else _get_ios_prompt_rules()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a mobile test automation expert. Respond only with valid JSON."
            },
            {
                "role": "user",
                "content": (
                    f"다음 Appium selector가 실패했습니다: {failed_selector}\n"
                    f"플랫폼: {platform}\n"
                    f"찾으려는 요소: {section} 섹션의 {key}\n\n"
                    f"현재 page_source (XML):\n{page_source}\n\n"
                    "안정성 순으로 최대 3개 제안해주세요. 확실하지 않으면 포함하지 마세요.\n"
                    f"{rules}"
                )
            }
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    return result.get("selectors", [])


def _update_locator_json_app(platform: str, section: str, key: str,
                              new_selector: str, old_selector: str,
                              extra_fallbacks: list[str] = None):
    with open(LOCATOR_FILE, encoding="utf-8") as f:
        locators = json.load(f)

    entry = locators[section][key][platform]
    entry["previous"] = old_selector
    entry["primary"] = new_selector
    entry["healed"] = True

    if extra_fallbacks:
        existing = entry.get("fallback") or []
        if isinstance(existing, str):
            existing = [existing]
        seen = set()
        deduped = [f for f in extra_fallbacks if not (f in seen or seen.add(f))]
        merged = deduped + [f for f in existing if f not in seen and f != new_selector]
        entry["fallback"] = merged
        print(f"[App-Healing] fallback 업데이트 → {merged}")

    with open(LOCATOR_FILE, "w", encoding="utf-8") as f:
        json.dump(locators, f, ensure_ascii=False, indent=2)


def try_heal_primary_app(driver, platform: str, section: str, key: str,
                          failed_primary: str, fallback_selector: str) -> bool:
    """
    fallback으로 요소를 찾은 뒤 호출.
    AI로 새 primary를 제안받아 locators_app.json 업데이트.
    """
    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from base_app_page import _parse_selector

    full_key = f"{platform}.{section}.{key}"
    counts = _load_heal_counts()

    if counts.get(full_key, 0) >= MAX_HEAL_COUNT:
        print(f"[App-Healing] {full_key} — healing {MAX_HEAL_COUNT}회 초과. 수동 확인 필요")
        return False

    print(f"[App-Healing] {full_key}: fallback 성공 → OpenAI로 새 primary 탐색")
    candidates = heal_locator_app(driver, platform, section, key, failed_primary)

    for i, c in enumerate(candidates, 1):
        print(f"[App-Healing] AI 후보 {i}순위: {c}")

    for i, candidate in enumerate(candidates):
        try:
            by, value = _parse_selector(candidate)
            WebDriverWait(driver, 2).until(EC.presence_of_element_located((by, value)))

            extra_fallbacks = [c for c in candidates[i + 1:] if c != candidate]
            _update_locator_json_app(platform, section, key, candidate, failed_primary, extra_fallbacks)
            counts[full_key] = counts.get(full_key, 0) + 1
            _save_heal_counts(counts)

            print(f"[App-Healing] {full_key} 새 primary 업데이트: {candidate}")
            print(f"[App-Healing] locators_app.json 업데이트됨 — PR 전 수동 검토 필요")
            return True

        except Exception:
            continue

    counts[full_key] = counts.get(full_key, 0) + 1
    _save_heal_counts(counts)
    print(f"[App-Healing] {full_key} — 새 primary 후보 모두 실패: {candidates}")
    return False
```

---

## 7. conftest.py Appium fixture

`conftest_app.py` — 기존 `conftest.py`와 별도 파일로 분리

```python
"""
Appium driver fixture

사용 방법:
    pytest tests_app/ --platform=android
    pytest tests_app/ --platform=ios
    pytest tests_app/ --platform=android --env=prod
"""

import json
import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions


def pytest_addoption(parser):
    parser.addoption("--platform", default="android", choices=["android", "ios"])
    parser.addoption("--env", default="qa", choices=["qa", "prod"])


def _load_env(env: str, platform: str) -> dict:
    with open("env.json", encoding="utf-8") as f:
        envs = json.load(f)
    return envs.get(env, {}).get(platform, {})


@pytest.fixture(scope="function")
def app_driver(request):
    platform = request.config.getoption("--platform")
    env = request.config.getoption("--env")
    env_config = _load_env(env, platform)

    if platform == "android":
        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.device_name = env_config.get("device_name", "emulator-5554")
        options.app = env_config.get("app_path", "")          # APK 경로
        options.app_package = env_config.get("app_package", "")
        options.app_activity = env_config.get("app_activity", "")
        options.no_reset = True                                 # 앱 데이터 유지
        options.auto_grant_permissions = True

    elif platform == "ios":
        options = XCUITestOptions()
        options.platform_name = "iOS"
        options.device_name = env_config.get("device_name", "iPhone 15")
        options.platform_version = env_config.get("ios_version", "17.0")
        options.app = env_config.get("app_path", "")           # .app 또는 .ipa 경로
        options.no_reset = True
        options.automation_name = "XCUITest"

    driver = webdriver.Remote("http://localhost:4723", options=options)
    driver.implicitly_wait(0)  # 명시적 wait 사용, implicit wait 비활성화

    yield driver

    # 실패 시 스크린샷 저장
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        driver.save_screenshot(f"screenshots/{request.node.name}.png")

    driver.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
```

### env.json 확장 (앱 설정 추가)

```json
{
  "qa": {
    "pc": { "base_url": "https://accounts.hanatour.com" },
    "mobile": { "base_url": "https://m.hanatour.com" },
    "android": {
      "device_name": "emulator-5554",
      "app_package": "com.hanatour.app",
      "app_activity": ".MainActivity",
      "app_path": "apps/hanatour-qa.apk"
    },
    "ios": {
      "device_name": "iPhone 15",
      "ios_version": "17.0",
      "app_path": "apps/hanatour-qa.app"
    }
  },
  "prod": {
    "android": {
      "device_name": "emulator-5554",
      "app_package": "com.hanatour.app",
      "app_activity": ".MainActivity",
      "app_path": "apps/hanatour-prod.apk"
    },
    "ios": {
      "device_name": "iPhone 15",
      "ios_version": "17.0",
      "app_path": "apps/hanatour-prod.ipa"
    }
  }
}
```

---

## 8. locators_app.json 예시

```json
{
  "login": {
    "email_input": {
      "android": {
        "primary": "accessibility id=email_input",
        "fallback": [
          "id=com.hanatour.app:id/input_email",
          "//android.widget.EditText[@hint='이메일을 입력하세요']"
        ],
        "previous": null,
        "healed": false
      },
      "ios": {
        "primary": "accessibility id=email_input",
        "fallback": [
          "-ios predicate string:type == 'XCUIElementTypeTextField' AND placeholderValue == '이메일을 입력하세요'"
        ],
        "previous": null,
        "healed": false
      }
    },
    "password_input": {
      "android": {
        "primary": "accessibility id=password_input",
        "fallback": [
          "id=com.hanatour.app:id/input_password"
        ],
        "previous": null,
        "healed": false
      },
      "ios": {
        "primary": "accessibility id=password_input",
        "fallback": [
          "-ios predicate string:type == 'XCUIElementTypeSecureTextField'"
        ],
        "previous": null,
        "healed": false
      }
    },
    "submit_btn": {
      "android": {
        "primary": "accessibility id=login_button",
        "fallback": [
          "id=com.hanatour.app:id/btn_login",
          "//android.widget.Button[@text='로그인']"
        ],
        "previous": null,
        "healed": false
      },
      "ios": {
        "primary": "accessibility id=login_button",
        "fallback": [
          "-ios predicate string:type == 'XCUIElementTypeButton' AND label == '로그인'"
        ],
        "previous": null,
        "healed": false
      }
    }
  }
}
```

---

## 9. 테스트 코드 예시

`tests_app/test_login_app.py` — 현재 `tests/test_login.py`와 동일한 패턴

```python
import pytest
from scripts_app.login_app_page import LoginAppPage


@pytest.fixture
def login_page(app_driver, request):
    platform = request.config.getoption("--platform")
    return LoginAppPage(app_driver, platform)


def test_login_success(login_page):
    login_page.enter_email("test@example.com")
    login_page.enter_password("password123")
    login_page.tap_submit()
    assert login_page.is_home_visible()


def test_login_empty_email(login_page):
    login_page.enter_password("password123")
    login_page.tap_submit()
    assert login_page.is_email_error_visible()
```

`scripts_app/login_app_page.py`

```python
from scripts.base_app_page import BaseAppPage


class LoginAppPage(BaseAppPage):

    def enter_email(self, email: str):
        self.fill("login", "email_input", email)

    def enter_password(self, password: str):
        self.fill("login", "password_input", password)

    def tap_submit(self):
        self.tap("login", "submit_btn")

    def is_home_visible(self) -> bool:
        return self.is_visible("home", "main_banner")

    def is_email_error_visible(self) -> bool:
        return self.is_visible("login", "error_email")
```

---

## 10. CI 설정 고려사항

### Healing 비활성화 (CI 필수)
```bash
# CI 파이프라인에서 healing 비활성화
DISABLE_HEALING=1 pytest tests_app/
```

`base_app_page.py`에 아래 조건 추가:
```python
if os.getenv("OPENAI_API_KEY") and not os.getenv("DISABLE_HEALING"):
    # healing 시도
```

### race condition (xdist 병렬 실행)
- 웹과 동일하게 `filelock`으로 `locators_app.json` 쓰기 시 lock 처리
- 또는 CI에서 병렬 실행 시 healing 비활성화

### 실기기 vs 에뮬레이터
- CI: 에뮬레이터 (GitHub Actions + Android emulator action)
- 실기기 테스트: BrowserStack App Automate 또는 AWS Device Farm 활용 가능
  - Appium 서버 URL만 교체하면 동작 (`http://hub.browserstack.com/wd/hub`)

---

## 11. 현재 코드와의 차이 요약

| 항목 | Playwright (현재) | Appium (확장) |
|---|---|---|
| 요소 탐색 | `page.locator(selector)` | `WebDriverWait` + `EC.presence_of_element_located` |
| 대기 | `locator.wait_for(timeout=5000)` | `WebDriverWait(driver, 5).until(...)` |
| 네비게이션 대기 | `wait_for_load_state("networkidle")` | 없음 — 앱 전환 후 특정 요소 출현으로 대기 |
| DOM 추출 | `page.evaluate("() => document.querySelector('form').innerHTML")` | `driver.page_source` (XML 전체) |
| selector 문법 | `#id`, `role=button[name=...]`, `.class` | `accessibility id=`, `id=pkg:id/res`, xpath |
| locators.json | 단일 구조 | `android` / `ios` 플랫폼 분기 |
| Healing 파일 | `.heal_count.json` | `.heal_count_app.json` (웹과 분리) |
| 플랫폼 감지 | 불필요 | `platform` 파라미터로 명시 |
| 키보드 처리 | 자동 | `driver.hide_keyboard()` 명시 필요 |
| 스크롤 | `page.evaluate("window.scrollBy")` | `driver.swipe()` |

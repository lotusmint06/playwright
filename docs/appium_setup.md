# Appium 구현 가이드

> **상태: ✅ 완료** (2026-04-06)  
> Playwright 프레임워크의 핵심 개념(locators.json + primary/fallback + AI healing)을  
> Appium Android 테스트에 적용한 구현 문서.

---

## 목차

1. [환경 설치](#1-환경-설치)
2. [Appium 서버 실행](#2-appium-서버-실행)
3. [프로젝트 구조](#3-프로젝트-구조)
4. [app_locators.json 구조](#4-app_locatorsjson-구조)
5. [BaseAppPage](#5-baseapppage)
6. [app_self_healing.py](#6-app_self_healingpy)
7. [conftest.py — Appium fixture](#7-conftestpy--appium-fixture)
8. [테스트 작성 방법](#8-테스트-작성-방법)
9. [웹 vs 앱 구현 비교](#9-웹-vs-앱-구현-비교)
10. [디버깅 도구](#10-디버깅-도구)

---

## 1. 환경 설치

### 필수 설치

```bash
# Node.js (Appium 서버 의존성)
brew install node

# Appium 서버
npm install -g appium

# Android 드라이버
appium driver install uiautomator2

# iOS 드라이버 (macOS 전용)
appium driver install xcuitest

# Android SDK (adb 포함)
brew install --cask android-platform-tools

# JDK (Android 필수)
brew install openjdk@17
```

### 환경변수 (`~/.zshrc`)

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$JAVA_HOME/bin:$PATH
export PATH=$ANDROID_HOME/platform-tools:$PATH
```

### Python 패키지

`requirements.txt`에 포함됨:
```
appium-python-client==5.3.0
```

### 설치 진단

```bash
npm install -g @appium/doctor
appium-doctor --android
```

`ANDROID_HOME`, `JAVA_HOME`, `adb` 항목이 ✔이면 기본 실행 가능.

---

## 2. Appium 서버 실행

프로젝트 루트의 `appium.config.json`으로 실행:

```bash
appium --config appium.config.json
```

`appium.config.json` 주요 설정:
```json
{
  "server": {
    "port": 4723,
    "allow-insecure": ["*:chromedriver_autodownload", "uiautomator2:adb_shell"],
    "default-capabilities": {
      "appium:noReset": true,
      "appium:newCommandTimeout": 300
    }
  }
}
```

---

## 3. 프로젝트 구조

```
app_locators.json        # 앱 selector 중앙 관리
app_self_healing.py      # XML 파싱 기반 앱 self-healing
appium.config.json       # Appium 서버 설정
env.json                 # android/ios 디바이스 설정 포함
scripts_app/
  base_app_page.py       # Appium 공통 액션 (탭/텍스트/가시성)
  main_page.py           # 메인화면 Page Object
tests_app/
  conftest.py            # Appium fixture
  test_connection.py     # 디바이스 연결 확인
  test_main.py           # 앱 기능 테스트
```

---

## 4. app_locators.json 구조

웹 `locators.json`과 동일한 구조, selector 형식만 다름.

```json
{
  "splash": {
    "splash_image": {
      "primary": "accessibility_id:배달의민족 앱을 시작합니다.",
      "fallback": "xpath://android.widget.ImageView[@content-desc='배달의민족 앱을 시작합니다.']",
      "previous": null,
      "healed": false
    }
  },
  "main": {
    "pizza_btn": {
      "primary": "accessibility_id:피자",
      "fallback": [
        "uiautomator:new UiSelector().description(\"피자\")",
        "xpath://android.widget.Button[@content-desc='피자']"
      ],
      "previous": null,
      "healed": false
    }
  }
}
```

### selector 접두사

| 접두사 | 전략 | 우선순위 |
|---|---|---|
| `accessibility_id:` | content-desc 기반 | 1순위 (가장 안정적) |
| `uiautomator:` | UiSelector 표현식 | 2순위 |
| `id:` | resource-id 기반 | resource-id 있을 때 |
| `xpath:` | XPath | 최후 수단 |

**금지**: 인덱스 기반 XPath (`//LinearLayout[2]`), `bounds` 기반 selector

---

## 5. BaseAppPage

`scripts_app/base_app_page.py` — 웹 `BasePage`의 Appium 버전.

### 탐색 순서

```
primary 시도 (WebDriverWait 15초)
    ✅ 성공 → 반환
    ❌ 실패 → fallback 순차 시도 (7초)
                 ✅ 성공 → [OPENAI_API_KEY 있을 때] app-healing
                 │              └─ XML 컨텍스트 추출
                 │              └─ AI로 새 primary 제안
                 │              └─ app_locators.json 업데이트 + 리로드
                 │          → 반환
                 ❌ 실패 → 다음 fallback ...
                              ❌ 모두 실패 → Exception
```

### StaleElement 재시도

`tap()` 메서드는 `StaleElementReferenceException` 발생 시 최대 3회 재탐색:

```python
def tap(self, section: str, key: str):
    for attempt in range(3):
        try:
            self.get_element(section, key).click()
            return
        except StaleElementReferenceException:
            if attempt == 2:
                raise
```

화면 전환 직후 요소를 클릭할 때 DOM 참조가 무효화되는 문제를 처리합니다.

### 새 Page Object 작성

```python
from scripts_app.base_app_page import BaseAppPage

class MyPage(BaseAppPage):
    def tap_some_button(self):
        self.tap("section", "button_key")

    def get_title_text(self) -> str:
        return self.get_text("section", "title_key")
```

---

## 6. app_self_healing.py

웹 `self_healing.py`의 Appium 버전. HTML 대신 XML을 파싱합니다.

### 웹과의 차이점

| 항목 | 웹 (self_healing.py) | 앱 (app_self_healing.py) |
|---|---|---|
| 컨텍스트 추출 | `page.evaluate()` → HTML | `driver.page_source` → XML |
| 파싱 | JS DOM 조작 | `xml.etree.ElementTree` |
| 요소 탐색 | CSS selector | content-desc / resource-id |
| AI 프롬프트 | Playwright selector | Appium selector 형식 |
| 검증 | `page.locator().wait_for()` | `driver.find_element()` |
| JSON 파일 | `locators.json` | `app_locators.json` |
| heal_count 파일 | `.heal_count.json` | `.app_heal_count.json` |

### XML 컨텍스트 추출

fallback selector 타입에 따라 XML에서 대상 요소를 직접 탐색:

```
accessibility_id: → @content-desc 탐색
id:               → @resource-id 탐색
uiautomator:      → description("값") 파싱 후 @content-desc 탐색
xpath:            → @content-desc 또는 @resource-id 값 추출 후 탐색
```

탐색 성공 시 `[대상 요소]` + `[주변 구조]` (부모 3단계) 분리 전달. 실패 시 전체 XML 4000자.

### AI 프롬프트 출력 형식

```json
{"selectors": [
  "accessibility_id:피자",
  "uiautomator:new UiSelector().description(\"피자\")",
  "xpath://android.widget.Button[@content-desc='피자']"
]}
```

순서 강제: 1순위 `accessibility_id:` → 2순위 `uiautomator:` → 3순위 `xpath:`

---

## 7. conftest.py — Appium fixture

```python
@pytest.fixture(scope="function")
def app_driver(pytestconfig):
    # 1. 디바이스/앱 설정 로드 (env.json)
    # 2. Appium 세션 생성
    # 3. 앱 상태 확인 → 실행 중이면 terminate → activate
    # 4. 스플래시 소멸 대기 (app_locators.json > splash.splash_image)
    yield driver
    driver.quit()
```

### 스플래시 대기

스플래시 화면의 고유 요소(`splash.splash_image`)가 사라질 때까지 대기합니다.  
selector는 `app_locators.json`에서 읽어 사용하므로, 변경 시 JSON만 수정하면 됩니다.

### env.json Android 설정

```json
"android": {
  "device_name": "R3CR20BA06Y",
  "platform_version": "13",
  "app_package": "com.sampleapp",
  "app_activity": "com.sampleapp.AppIconDefault",
  "app_path": ""
}
```

---

## 8. 테스트 작성 방법

1. `app_locators.json`에 섹션/요소 추가
2. `scripts_app/`에 Page Object 작성 (`BaseAppPage` 상속)
3. `tests_app/`에 테스트 작성 (`assert`만 사용)

### 예시

**app_locators.json**
```json
{
  "login": {
    "email_input": {
      "primary": "accessibility_id:이메일 입력",
      "fallback": ["uiautomator:new UiSelector().description(\"이메일 입력\")"],
      "previous": null,
      "healed": false
    }
  }
}
```

**scripts_app/login_page.py**
```python
from scripts_app.base_app_page import BaseAppPage

class LoginAppPage(BaseAppPage):
    def enter_email(self, email: str):
        el = self.get_element("login", "email_input")
        el.send_keys(email)
```

**tests_app/test_login.py**
```python
from scripts_app.login_page import LoginAppPage

def test_login_ui_visible(app_driver):
    page = LoginAppPage(app_driver)
    assert page.is_displayed("login", "email_input")
```

---

## 9. 웹 vs 앱 구현 비교

| 항목 | 웹 (Playwright) | 앱 (Appium) |
|---|---|---|
| selector 파일 | `locators.json` | `app_locators.json` |
| Page Object 기반 | `BasePage` | `BaseAppPage` |
| self-healing | `self_healing.py` | `app_self_healing.py` |
| 컨텍스트 | HTML (`page.evaluate`) | XML (`driver.page_source`) |
| 대기 방식 | `locator.wait_for(timeout)` | `WebDriverWait + EC` |
| 클릭 | `locator.click()` | `element.click()` + stale retry |
| heal_count | `.heal_count.json` | `.app_heal_count.json` |
| 스플래시 대기 | 없음 | `EC.invisibility_of_element_located` |

---

## 10. 디버깅 도구

### 현재 화면 XML 덤프

```bash
adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml
```

### 포그라운드 앱/액티비티 확인

```bash
adb shell dumpsys window | grep mCurrentFocus
```

### 설치된 앱 목록

```bash
adb shell pm list packages -3           # 서드파티 앱
adb shell dumpsys package | grep <키워드>  # 패키지명 검색
```

### Appium Inspector

GUI로 XML 계층 탐색 및 selector 확인. 실행 중인 Appium 서버에 연결해 사용.

- 요소 클릭 시 `accessibility_id`, `uiautomator`, `xpath` selector 자동 제공
- `content-desc`가 있으면 `accessibility_id`를 1순위로 선택

# TODO

## 목차

1. [현황 평가](#현황-평가-100점-만점)
2. [Self-Healing 접근법에 대한 고려사항](#self-healing-접근법에-대한-고려사항)
3. [우선순위별 작업 목록](#우선순위별-작업-목록)
   - 🔴 [즉시] is_visible 버그 / 버전 고정 / pytest-playwright 충돌
   - 🟡 [단기] click 구분 / race condition / dead code
   - 🟢 [장기] env 분리 / DOM adaptive / regex 개선 / 테스트 커버리지
4. [AI 기반 자율 테스트 실행 (LLM-driven Test Agent)](#ai-기반-자율-테스트-실행-llm-driven-test-agent)
5. [Locator 사전 생성 도구 (generate_locator)](#locator-사전-생성-도구-generate_locator)
6. [Appium 확장 가능성](#appium-확장-가능성)
7. [Self-Healing DOM Context 최적화](#self-healing-dom-context-최적화)

---

## 현황 평가 (100점 만점)

| 항목 | 점수 | 평가 요약 |
|---|---|---|
| **구조** | 68 | 레이어 분리는 명확하나 `is_visible()` 버그, dead code(session_page) 존재 |
| **효율성** | 58 | 모든 클릭에 networkidle 대기, DOM 4000자 고정 컷, 불필요한 패키지 포함 |
| **안정성** | 52 | 버전 미고정, xdist race condition 미대응, `pytest-playwright` 충돌 가능성 |
| **확장성** | 45 | 로그인 페이지만 존재, QA/Prod URL 동일, validate_locators regex 한계 |
| **종합** | **56** | 아이디어와 방향은 좋으나 안정성·확장성 보강 전에 페이지 추가는 리스크 |

---

## Self-Healing 접근법에 대한 고려사항

### 좋은 점
- **Self-healing 아이디어 자체는 유효** — 선택자가 자주 바뀌는 SPA 환경에서 유지보수 부담을 줄여줌
- **locators.json 중앙화** — 선택자를 코드에서 분리한 건 올바른 설계
- **healed: true 플래그** — AI가 바꾼 건 수동 검토하도록 강제하는 게 안전장치로 적절

### 현실적인 우려

#### 1. AI 의존성이 테스트 신뢰성을 낮춤
- 테스트의 본질은 "이 기능이 지금 동작하는가?"인데, selector가 깨졌을 때 AI가 고치면 **실제 버그를 숨길 수 있음**
- 예: 로그인 버튼 ID가 바뀐 게 배포 실수라면, self-healing이 자동으로 통과시켜버릴 수 있음
- **대응 방향**: healing 성공 시 Slack/Teams 알림 + healed 항목 PR 필수 검토 강제화

#### 2. 비결정적(non-deterministic) 테스트
- 같은 코드인데 API 키 있으면 동작, 없으면 실패 — CI 환경에 따라 결과가 달라짐
- **대응 방향**: CI에서는 `DISABLE_HEALING=1` 옵션으로 healing 완전 비활성화, 로컬에서만 활성화

#### 3. GPT-4o-mini 호출 비용과 속도
- 테스트 실패마다 OpenAI API 호출 → CI 파이프라인이 느려지고 비용이 예측 불가
- 대규모 테스트 스위트에서는 문제가 됨
- **대응 방향**: 위와 동일 (CI healing 비활성화), 또는 실패 횟수 임계값 이후에만 healing 시도

#### 4. 근본 해결이 아닌 임시방편
- 선택자가 자주 깨진다면 그건 **프론트엔드에 안정적인 test-id가 없다는 신호**
- `data-testid` 같은 명시적 attribute를 프론트팀과 협의해서 추가하는 게 self-healing보다 근본적인 해결책
- **대응 방향**: 프론트팀에 `data-testid` 도입 제안 검토

### 접근법별 추천 여부

| 상황 | 추천 여부 |
|---|---|
| 레거시 사이트, 프론트 수정 불가 (현재 상황) | ✅ 합리적인 선택 |
| 새 프로젝트, 프론트팀 협업 가능 | ❌ `data-testid` 먼저 도입 |
| CI 안정성이 최우선 | ❌ healing은 로컬 전용으로 제한 |

---

## 우선순위별 작업 목록

### 🔴 즉시 (버그 / 안정성 위험)

#### 1. `is_visible()` fallback 미반영 버그
- **파일**: `scripts/base_page.py`
- **문제**: primary 깨진 상태면 요소가 실제로 있어도 `False` 반환
- **수정**: `page.locator(selector).is_visible()` → `get_locator()` 결과 사용으로 교체
- **영향**: `is_submit_btn_visible()`, `is_error_popup_visible()` 등 모든 visibility 체크

#### 2. requirements.txt 버전 고정
- **파일**: `requirements.txt`
- **문제**: 버전 없으면 CI에서 언제든 깨질 수 있음 (`openai` 1.x → 2.x API 변경 사례 있음)
- **수정**: `pip freeze > requirements.txt` 또는 주요 패키지 버전 명시
  ```
  playwright==1.x.x
  openai==2.x.x
  pytest==x.x.x
  ```

#### 3. `pytest-playwright` vs `sync_playwright` 통일
- **파일**: `requirements.txt`, `conftest.py`
- **문제**: `pytest-playwright` 설치돼 있지만 `sync_playwright` 직접 사용 중 — 충돌 가능성
- **수정**: `pytest-playwright` 제거하거나, 반대로 fixture를 `pytest-playwright` 방식으로 전환

---

### 🟡 단기 (효율성 / 구조 개선)

#### 4. `click()` 네비게이션 여부 구분
- **파일**: `scripts/base_page.py`
- **문제**: 체크박스, 토글 등 단순 UI 변경에도 networkidle 대기 — 불필요한 지연
- **수정**: `click()`은 그대로 유지, `click_and_navigate()`를 별도로 만들어 네비게이션이 예상되는 경우에만 사용

#### 5. xdist 병렬 실행 시 locators.json race condition
- **파일**: `self_healing.py`, `scripts/base_page.py`
- **문제**: 여러 worker가 동시에 locators.json 읽기/쓰기 시 데이터 손상 가능
- **수정**: `filelock` 라이브러리로 쓰기 시 lock 처리, 또는 CI에서 healing 비활성화 옵션 추가

#### 6. `session_page` fixture dead code
- **파일**: `conftest.py`
- **문제**: 실제로 사용하는 테스트 없음
- **수정**: 로그인 유지가 필요한 테스트 작성 후 활용하거나, 준비 안 됐으면 제거

---

### 🟢 장기 (확장성)

#### 7. env.json QA/Prod URL 분리
- **파일**: `env.json`
- **문제**: QA/Prod base_url이 동일 — `--env` 옵션이 의미 없음
- **수정**: 실제 QA 도메인 추가

#### 8. DOM 추출 adaptive sizing
- **파일**: `self_healing.py` — `_get_element_context()`
- **문제**: 4000자 고정 — 복잡한 페이지에서 중요 요소가 잘릴 수 있음
- **수정**: fallback 성공 요소의 부모 3단계 HTML만 추출 → 토큰 절약 + 정확도 향상
- *(상세 구현은 아래 Self-Healing DOM Context 최적화 섹션 참고)*

#### 9. validate_locators regex 개선
- **파일**: `validate_locators.py`
- **문제**: `self.locators["section"]["key"]` 패턴을 `\w+`로 잡아서 특수문자 포함 key 누락
- **수정**: `[\w\-]+` 또는 따옴표 안 문자열 전체를 캡처하도록 수정

#### 10. 테스트 커버리지 확대
- **파일**: `tests/`, `scripts/`, `locators.json`
- **현재**: 로그인 페이지 8개 테스트만 존재
- **추가 필요**:
  - 네이버/카카오/애플 소셜 로그인 버튼 동작 확인
  - 아이디 저장 체크박스 동작
  - 빈 필드 제출 시 에러 메시지 텍스트 검증

---

## AI 기반 자율 테스트 실행 (LLM-driven Test Agent)

locators.json에 description을 추가하고 BasePage 메서드를 LLM tool로 노출해,
자연어 테스트 케이스를 LLM이 직접 실행하는 구조.

### 개념 구조

```
locators.json (description 추가)
    +
BasePage 메서드 → LLM tools로 노출
    +
자연어 테스트 케이스 입력
    ↓
LLM이 tools 호출하면서 테스트 실행
```

### locators.json 확장 방향
```json
{
  "login": {
    "email_input": {
      "primary": "#input03",
      "fallback": ["..."],
      "description": "이메일 입력 필드"
    },
    "submit_btn": {
      "primary": "#btnLogin",
      "description": "로그인 버튼 — 클릭 시 인증 시도"
    }
  }
}
```

### Tools 노출 예시
```python
tools = [
  {"name": "click",      "description": "요소 클릭", ...},
  {"name": "fill",       "description": "텍스트 입력", ...},
  {"name": "is_visible", "description": "요소 표시 여부 확인", ...},
  {"name": "assert_url", "description": "현재 URL 검증", ...}
]
```

### 잘 되는 영역
- **탐색적 테스트** — "이 페이지에서 뭔가 이상한 거 찾아봐"
- **테스트 코드 생성** — 자연어 → pytest 코드 자동 작성 후 결정적 실행
- **신규 페이지 빠른 커버리지** — description만 잘 써있으면 LLM이 흐름 파악 가능

### 한계

| 문제 | 이유 |
|---|---|
| 비결정적 실행 | 같은 입력도 LLM 응답이 매번 다를 수 있음 |
| assertion 신뢰성 | LLM이 "통과"라고 판단해도 실제 버그일 수 있음 |
| 속도/비용 | 스텝마다 API 호출 → 느리고 비쌈 |
| 디버깅 어려움 | 왜 그 tool을 선택했는지 추적 힘듦 |

### 권장 hybrid 접근
LLM을 런타임 실행자가 아닌 **코드 생성기**로 사용:
```
자연어 → LLM → pytest 코드 생성 (1회)
                    ↓
            이후는 코드가 결정적으로 실행
```

### 유사 프로젝트 참고
- **Browser Use** — Python, LLM + Playwright 조합으로 거의 이 개념 그대로 구현
- **Stagehand** (Browserbase) — 같은 방향, JS 생태계
- **Playwright MCP** — Claude가 직접 브라우저 조작

---

## Locator 사전 생성 도구 (generate_locator)

테스트 실패를 기다리지 않고, **사전에 능동적으로** 선택자를 생성해 locators.json에 등록하는 도구.
기존 `self_healing.py`의 `heal_locator()`, `_update_locator_json()`을 재사용하므로 추가 코드가 적음.

### 사용 방식

```bash
# URL 직접 접속 → Playwright로 DOM 추출 → 선택자 생성
python generate_locator.py --section login --key email_input --url https://accounts.hanatour.com

# DOM 직접 붙여넣기 (브라우저 없이)
python generate_locator.py --section login --key email_input --dom "<form>...</form>"
```

### 내부 흐름

```
URL 입력 → Playwright로 페이지 열기 → DOM 추출
DOM 입력 → 그대로 사용
    ↓
heal_locator() 호출 (기존 코드 재사용)
    ↓
1,2,3순위 후보 순서대로 page.locator().wait_for() 시도
    ↓
성공한 것 → primary, 나머지 → fallback으로 locators.json 업데이트
```

### 구현 방식 비교

| | CLI 스크립트 | Playwright MCP |
|---|---|---|
| 구현 난이도 | 낮음 (기존 코드 재사용) | 중간 (MCP 서버 설정 필요) |
| 사용 편의성 | 터미널 명령어 | 대화형 (Claude와 직접 대화) |
| 브라우저 필요 | 선택 (URL or DOM 중 택1) | 항상 필요 |
| 우선 구현 | ✅ | 추후 검토 |

### 관련 파일
- `self_healing.py` — `heal_locator()`, `_update_locator_json()` 재사용
- `generate_locator.py` — 신규 작성 (진입점만 추가)

---

## Appium 확장 가능성

이 프레임워크의 핵심 개념(locators.json + primary/fallback + AI healing)은 Appium 모바일 테스트에도 적용 가능.
웹보다 앱이 업데이트마다 selector가 더 자주 바뀌어 오히려 더 필요한 영역.

### 그대로 재사용 가능한 것
- `locators.json` 구조 (primary / fallback / healed)
- heal_count 제한, healed 플래그 검토 프로세스
- AI에게 컨텍스트 넘겨서 selector 제안받는 흐름

### 변경 필요한 것

#### DOM 추출
```python
# Playwright
page.evaluate("() => document.querySelector('form').innerHTML")  # HTML

# Appium
driver.page_source  # XML (UIAutomator / XCUITest) — 훨씬 크므로 컷 기준 강화 필요
```

#### Locator 전략

| 우선순위 | Playwright | Appium |
|---|---|---|
| 1순위 | `#id` | `accessibility id` |
| 2순위 | `role=button[name=...]` | `id` (resource-id) |
| 3순위 | `.static-class` | `-android uiautomator` / `-ios predicate` |
| 금지 | `data-v-*` | 인덱스 기반 xpath (`//LinearLayout[2]`) |

#### locators.json 플랫폼 분기
```json
{
  "login": {
    "email_input": {
      "android": { "primary": "accessibility id=email", "fallback": "..." },
      "ios":     { "primary": "accessibility id=email", "fallback": "..." }
    }
  }
}
```

#### AI 프롬프트 추가 지침
```
"accessibility id=..." 또는 "id=com.example.app:id/..."
xpath는 텍스트 기반만 허용: //*[@text='로그인']
인덱스 기반 xpath는 절대 사용하지 마세요: //LinearLayout[2]
```

### 구현 시 고려사항
- `BasePage`를 `BaseAppPage`로 상속 확장하여 Appium driver 대응
- `wait_for()` → `WebDriverWait` + `ExpectedConditions` 로 교체
- iOS / Android 플랫폼 감지 후 적절한 locator 선택 로직 추가
- CI healing 비활성화 옵션은 동일하게 적용

---

## Self-Healing DOM Context 최적화

### 배경
현재 `self_healing.py`의 `_get_element_context()`는 `form/main/body` 순서로 컨테이너를 찾아
최대 4000자를 OpenAI에 전송한다. 로그인 페이지처럼 단순한 페이지는 괜찮지만
검색 결과 등 DOM이 큰 페이지에서는 토큰 낭비가 발생한다.

### 개선 방향
primary, fallback 모두 실패했을 때:

```
primary 실패 → fallback 실패
    → page.evaluate(JS)로 실패한 요소 주변 HTML만 추출 (부모 3단계)
        → 4000자 이내로 OpenAI 전송
            → 새 selector 후보 받아서 순차 시도
                → 성공하면 primary + fallback 둘 다 업데이트
```

### 구현 포인트
- `page.evaluate(JS)`로 DOM 탐색은 브라우저(JS)가 수행, 결과값만 Python으로 반환
- fallback selector가 있으면 그 요소의 부모 3단계 HTML만 추출
- fallback도 없으면 title/placeholder 속성으로 관련 요소 검색 후 주변 추출
- 최후 수단으로 form → main → body 순서 (현재 방식)

### 관련 파일
- `self_healing.py` — `_get_element_context()` 함수 개선
- `scripts/base_page.py` — primary/fallback 모두 실패 시 `try_heal()` 호출 추가
- `locators.json` — fallback 필드 활용

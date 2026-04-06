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

> 마지막 업데이트: 2026-04-06

| 항목 | 이전 | 현재 | 평가 요약 |
|---|---|---|---|
| **구조** | 68 | **78** | `is_visible()` 버그 수정, conftest 3파일 분리, `click_and_navigate()` 분리 완료 |
| **효율성** | 58 | **75** | DOM 컨텍스트 최적화 완료 — 토큰 72% 절감, 오답 후보 제거. xdist race condition 잔존 |
| **안정성** | 52 | **72** | 버전 고정, `pytest-playwright` 충돌 제거 완료. xdist race condition 미대응 잔존 |
| **확장성** | 45 | **53** | Appium 확장 구조 문서화 및 conftest 기반 마련. URL 분리·커버리지 확대는 잔존 |
| **종합** | **56** | **70** | DOM 최적화로 self-healing 품질 향상. 남은 과제는 병렬 실행 안전성과 커버리지 확대 |

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

#### 1. ~~`is_visible()` fallback 미반영 버그~~ ✅ 완료
- `get_locator()` 경유로 교체, fallback·exception 처리 포함

#### 2. ~~requirements.txt 버전 고정~~ ✅ 완료
- 모든 패키지 버전 고정 (playwright==1.58.0, openai==2.30.0 등)

#### 3. ~~`pytest-playwright` vs `sync_playwright` 통일~~ ✅ 완료
- `pytest-playwright`, `pytest-base-url` 제거. `sync_playwright` 직접 사용으로 통일

---

### 🟡 단기 (효율성 / 구조 개선)

#### 4. ~~`click()` 네비게이션 여부 구분~~ ✅ 완료
- `click()` 단순 클릭, `click_and_navigate()` 분리. 네비게이션 유발 호출 모두 교체

#### 5. xdist 병렬 실행 시 locators.json race condition
- **파일**: `self_healing.py`, `scripts/base_page.py`
- **문제**: 여러 worker가 동시에 locators.json 읽기/쓰기 시 데이터 손상 가능
- **수정**: `filelock` 라이브러리로 쓰기 시 lock 처리, 또는 CI에서 healing 비활성화 옵션 추가

#### 6. `session_page` — 향후 활용 예정
- **파일**: `tests/conftest.py`
- **현황**: 로그인 상태 유지 테스트 작성 시 사용 예정으로 유지

---

### 🟢 장기 (확장성)

#### 7. env.json QA/Prod URL 분리
- **파일**: `env.json`
- **문제**: QA/Prod base_url이 동일 — `--env` 옵션이 의미 없음
- **수정**: 실제 QA 도메인 추가

#### 8. ~~DOM 추출 adaptive sizing~~ ✅ 완료
- `_get_element_context()`에 `[대상 요소]` + `[주변 구조]` 분리 전달 구현
- 토큰 72% 절감 (1,686 → 477), 오답 후보 제거 확인
- *(상세 내용은 [docs/dom_context_optimization.md](./docs/dom_context_optimization.md) 참고)*

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

## Self-Healing DOM Context 최적화 ✅ 완료

설계 배경, 구현 내용, 실측 결과는 **[docs/dom_context_optimization.md](./docs/dom_context_optimization.md)** 를 참고하세요.

### 요약
- `[대상 요소]` (요소 자체 HTML) + `[주변 구조]` (부모 3단계) 분리 전달
- 프롬프트에 "[대상 요소]의 selector만 제안" 명시 → 형제 요소 오답 제거
- 토큰 72% 절감 (1,686 → 477), selector 후보 품질 향상 확인
- 검증 도구: `tools/check_context.py`

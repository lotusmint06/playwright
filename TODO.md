# TODO

## 목차

1. [현황 평가](#현황-평가-100점-만점)
2. [Self-Healing 접근법에 대한 고려사항](#self-healing-접근법에-대한-고려사항)
3. [우선순위별 작업 목록](#우선순위별-작업-목록)
  - 🟡 [단기] race condition / CI healing 비활성화
  - 🟢 [장기] env 분리 / regex 개선 / 테스트 커버리지 / 이슈 자동 등록
4. [AI Test Agent — 투 트랙 전략](#ai-test-agent--투-트랙-전략)
5. [Playwright MCP 연동](#playwright-mcp-연동)
6. [Locator 사전 생성 도구 (generate_locator)](#locator-사전-생성-도구-generate_locator)
7. [Appium 확장 가능성](#appium-확장-가능성)
8. [Self-Healing DOM Context 최적화 ✅ 완료](#self-healing-dom-context-최적화--완료)

---

## 현황 평가 (100점 만점)

> 마지막 업데이트: 2026-04-06


| 항목      | 이전     | 현재     | 평가 요약                                                                            |
| ------- | ------ | ------ | -------------------------------------------------------------------------------- |
| **구조**  | 68     | **82** | `is_visible()` 버그 수정, conftest 3파일 분리, `scripts_app/` 구조 완성                      |
| **효율성** | 58     | **75** | DOM 컨텍스트 최적화 완료 — 토큰 72% 절감, 오답 후보 제거. xdist race condition 잔존                   |
| **안정성** | 52     | **74** | 버전 고정, 스플래시 감지, StaleElement retry, heal_count 분리 완료. xdist 잔존                   |
| **확장성** | 45     | **72** | Appium 확장 완료 — `BaseAppPage`, `app_self_healing.py`, `app_locators.json`, XML 파싱 |
| **종합**  | **56** | **76** | Appium 트랙 실사용 가능 수준 완성. 남은 과제는 병렬 실행 안전성과 커버리지 확대                                |


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


| 상황                         | 추천 여부                 |
| -------------------------- | --------------------- |
| 레거시 사이트, 프론트 수정 불가 (현재 상황) | ✅ 합리적인 선택             |
| 새 프로젝트, 프론트팀 협업 가능         | ❌ `data-testid` 먼저 도입 |
| CI 안정성이 최우선                | ❌ healing은 로컬 전용으로 제한 |


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
- **수정**: `filelock` 라이브러리로 쓰기 시 lock 처리

#### 6. `session_page` — 향후 활용 예정

- **파일**: `tests/conftest.py`
- **현황**: 로그인 상태 유지 테스트 작성 시 사용 예정으로 유지

#### 11. CI healing 비활성화 옵션 (`DISABLE_HEALING`)

- **파일**: `self_healing.py`, `conftest.py`
- **문제**: CI 환경에서 healing이 활성화되면 비결정적 실행 + locators.json git diff 항상 발생
- **수정**: `DISABLE_HEALING=1` 환경변수로 healing 완전 차단
  ```bash
  # CI에서
  DISABLE_HEALING=1 pytest tests/
  # 로컬에서 (healing 활성화)
  OPENAI_API_KEY=sk-... pytest tests/
  ```
- **연관**: Self-Healing 고려사항 항목 2 (비결정적 테스트)

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

#### 12. 테스트 실패 이슈 자동 등록

- **현재**: Teams webhook으로 통과/실패 건수만 전송
- **개선**: 실패한 테스트별로 GitHub Issue (또는 Jira) 자동 생성
  - 테스트명, 실패 로그, 스크린샷 경로 포함
  - 동일 이슈 중복 등록 방지 (제목 기반 중복 체크)
  - 라벨: `e2e-test-failure`, `bug`, `automated`
- **참고**: 엑셈 팀 `GitHubIssueService` 구현 사례 ([블로그](https://ex-em.com/en/blog/ai-test-code-automation-experience-lessons-learned))

---

## AI Test Agent — 투 트랙 전략

### 트랙 구조

```
Track 1 (현재) — CI 결정적 실행
    pytest → BasePage → locators.json → self-healing
    항상 같은 결과, 파이프라인 신뢰성 보장

Track 2 (확장) — Agent 코드 생성
    자연어 목표 → Sub-agent → locators.json 자동 등록 + pytest 코드 생성
                                    ↓
                            Track 1에 편입되어 결정적으로 실행
```

Agent가 CI를 직접 돌리는 게 아니라 **Track 1에서 돌아갈 코드를 만들어주는 역할**로 분리.
self-healing도 같은 철학 — LLM이 테스트를 통과시키는 게 아니라 locators.json을 수정하고 이후 결정적으로 실행.

### Claude Code Sub-agent 구조 (Track 2)

프레임워크 적용안:

```
개발자 (자연어 요청)
    ↓
Claude Code (메인 에이전트 + CLAUDE.md)
    ├─ @locator-generator   — 신규 페이지 locators.json 자동 생성
    ├─ @test-writer         — 시나리오 기반 pytest 코드 자동 작성
    └─ @healing-reviewer    — healed: true 항목 검토 및 수정 제안
```

`.claude/agents/` 디렉토리에 각 sub-agent 정의 파일 배치.

### locators.json `description` 필드 추가

Sub-agent가 어떤 요소인지 이해하려면 description이 필요:

```json
{
  "login": {
    "email_input": {
      "primary": "#input01",
      "fallback": ["role=textbox[name='아이디(이메일계정)']"],
      "description": "이메일(아이디) 입력 필드",
      "previous": null,
      "healed": false
    }
  }
}
```

### 잘 되는 영역

- **신규 페이지 빠른 커버리지** — URL 하나로 locators.json + 테스트 코드 초안 생성
- **탐색적 테스트** — "이 페이지에서 이상한 거 찾아봐"
- **healed 항목 일괄 검토** — `healed: true` 항목 diff 분석 후 수정 제안

### 한계


| 문제            | 이유                           |
| ------------- | ---------------------------- |
| 비결정적 실행       | 같은 입력도 LLM 응답이 매번 다를 수 있음    |
| assertion 신뢰성 | LLM이 "통과"라고 판단해도 실제 버그일 수 있음 |
| 속도/비용         | 스텝마다 API 호출 → 느리고 비쌈         |


### 참고

- **엑셈 팀 블로그** — Claude Code Sub-agent 기반 테스트 자동화 실제 구현 사례
- **Browser Use** — Python, LLM + Playwright 조합
- **Stagehand** (Browserbase) — 같은 방향, JS 생태계
- **Playwright MCP** — Claude가 직접 브라우저 조작 (아래 섹션 참고)

---

## Playwright MCP 연동

Claude Code에 `@playwright/mcp`를 등록하면 자연어로 브라우저를 직접 조작하고 E2E 테스트 코드를 생성할 수 있습니다.

### 설정

```bash
claude mcp add playwright npx @playwright/mcp@latest
```

### 활용 방향

```
"로그인 페이지 E2E 테스트 코드 작성해줘"
    ↓
Claude Code + Playwright MCP
    → 실제 브라우저 열어서 페이지 탐색
    → locators.json 기반으로 selector 확인
    → pytest 코드 생성 → Track 1에 편입
```

### CLI 방식 vs MCP 방식


|         | `generate_locator.py` (CLI) | Playwright MCP |
| ------- | --------------------------- | -------------- |
| 구현 난이도  | 낮음 (기존 코드 재사용)              | 설정 1줄          |
| 사용 편의성  | 터미널 명령어                     | Claude와 대화형    |
| 브라우저 필요 | 항상 필요 (URL 필수)             | 항상 필요          |
| 우선 구현   | ✅                           | 이후 병행          |


---

## Locator 사전 생성 도구 (generate_locator) ✅ 완료

> **범위: 웹(Playwright) 전용**  
> 앱(Appium)은 디바이스 연결 및 앱 실행 상태가 전제되어야 하고, content-desc 없는 요소가 많아 자동 생성 품질이 낮으므로 미지원.

테스트 실패를 기다리지 않고, **사전에 능동적으로** 선택자를 생성해 locators.json에 등록하는 도구.

### 사용 방식

```bash
python tools/generate_locator.py \
    --url https://example.com/login \
    --section login \
    --key email_input \
    --description "이메일 입력 필드"
```

### 내부 흐름

```
URL 입력 → Playwright로 페이지 열기 → DOM 추출 (정제)
    ↓
OpenAI(gpt-4o-mini)에 selector 후보 3개 요청
    ↓
후보를 순서대로 page.locator().wait_for() 검증
    ↓
성공한 첫 번째 → primary, 나머지 → fallback으로 locators.json 등록
```

### 관련 파일

- `tools/generate_locator.py` — 구현 완료

---

## Appium 확장 ✅ 완료

상세 구현 가이드는 **[docs/appium_setup.md](./docs/appium_setup.md)** 참고.

### 구현 완료 항목


| 항목               | 파일                             | 내용                                         |
| ---------------- | ------------------------------ | ------------------------------------------ |
| 앱 selector 관리    | `app_locators.json`            | primary / fallback 배열 / healed — 웹과 동일 구조  |
| 앱 Page Object 기반 | `scripts_app/base_app_page.py` | WebDriverWait, stale retry, app-healing 연동 |
| 앱 self-healing   | `app_self_healing.py`          | XML 파싱 + Appium 전용 프롬프트 + heal_count 분리    |
| Appium fixture   | `tests_app/conftest.py`        | 앱 종료→실행→스플래시 소멸 대기                         |
| 연결 테스트           | `tests_app/test_connection.py` | 세션/디바이스/화면/앱 실행 확인                         |
| 메인화면 테스트         | `tests_app/test_main.py`       | 피자 탭 → 뒤로가기                                |


### selector 접두사 규칙


| 접두사                 | 전략                    | 예시                                                  |
| ------------------- | --------------------- | --------------------------------------------------- |
| `accessibility_id:` | content-desc 기반 (1순위) | `accessibility_id:피자`                               |
| `uiautomator:`      | UiSelector (2순위)      | `uiautomator:new UiSelector().description("피자")`    |
| `id:`               | resource-id 기반        | `id:com.sampleapp:id/btn_login`                     |
| `xpath:`            | XPath (최후 수단)         | `xpath://android.widget.Button[@content-desc='피자']` |


### 남은 과제

- iOS 테스트 (XCUITest) 검증
- CI healing 비활성화 옵션 (`DISABLE_HEALING`) 앱에도 적용

---

## Self-Healing DOM Context 최적화 ✅ 완료

설계 배경, 구현 내용, 실측 결과는 **[docs/dom_context_optimization.md](./docs/dom_context_optimization.md)** 를 참고하세요.

### 요약

- `[대상 요소]` (요소 자체 HTML) + `[주변 구조]` (부모 3단계) 분리 전달
- 프롬프트에 "[대상 요소]의 selector만 제안" 명시 → 형제 요소 오답 제거
- 토큰 72% 절감 (1,686 → 477), selector 후보 품질 향상 확인
- 검증 도구: `tools/check_context.py`


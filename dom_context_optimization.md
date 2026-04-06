# DOM Context 최적화 설계

`self_healing.py`의 `_get_element_context()` 개선 설계 문서.

---

## 목차

1. [현재 방식과 문제점](#1-현재-방식과-문제점)
2. [개선 방향](#2-개선-방향)
3. [HTML 정제 항목](#3-html-정제-항목)
4. [추출 우선순위 로직](#4-추출-우선순위-로직)
5. [구현 코드](#5-구현-코드)
6. [실측 결과](#6-실측-결과-2026-04-04-기준)
7. [주의사항 및 엣지 케이스](#7-주의사항-및-엣지-케이스)
8. [변경 범위](#8-변경-범위)

---

## 1. 현재 방식과 문제점

### 현재 코드 (`self_healing.py:34`)

```python
def _get_element_context(page) -> str:
    context = page.evaluate("""
        () => {
            const containers = ['form', 'main', '[role=main]', 'body'];
            for (const selector of containers) {
                const el = document.querySelector(selector);
                if (el) return el.innerHTML;
            }
            return document.body.innerHTML;
        }
    """)
    return context[:4000]
```

### 문제점

**1. fallback 성공 정보를 무시**
`try_heal_primary()`는 `fallback_selector`로 이미 요소를 찾은 상태에서 호출되지만,
`_get_element_context()`는 이 정보를 받지 않고 `form/main/body` 전체를 긁습니다.

**2. 4000자 고정 컷**
복잡한 페이지에서는 목표 요소 주변 HTML이 잘려나갈 수 있습니다.
반대로 단순한 페이지에서는 불필요한 HTML이 토큰을 낭비합니다.

**3. 정제되지 않은 HTML 전송**
`style` 속성, `data-v-*` 해시, `<script>`, `<svg>` 등 selector 생성에 무관한 노이즈가
OpenAI 입력에 포함됩니다.

### 현재 추출 예시

```html
<!-- form.innerHTML[:4000] — 노이즈 포함 -->
<div class="input_wrap" style="margin-top:16px;padding:0 20px" data-v-3f8a2b1c>
  <label class="label_txt active focus" for="input01" data-v-3f8a2b1c>아이디(이메일계정)</label>
  <input id="input01" type="email" class="input_txt" placeholder="아이디(이메일계정)"
         onclick="this.select()" autocomplete="email" data-v-3f8a2b1c>
  <span class="error_id" style="display:none;color:#e00;font-size:12px">
    아이디(이메일계정)을 입력해주세요.
  </span>
  <!-- 이하 페이지의 나머지 요소들이 4000자 채울 때까지 포함됨 -->
  ...
</div>
```

---

## 2. 개선 방향

`fallback_selector`로 찾은 요소의 **부모 3단계 HTML만** 추출하고, 불필요한 속성과 태그를 정제합니다.

### 추출 전략 (우선순위)

```
1순위: fallback_selector 있음
       → locator.evaluate(JS)로 해당 요소의 부모 3단계 outerHTML 추출 후 정제

2순위: fallback_selector 없음 (heal_locator 경로)
       → form/main/body 순서로 innerHTML 추출 후 정제

공통: 추출 후 HTML 정제 (style, 해시 속성, 긴 텍스트 등 제거)
      → 최대 4000자 컷 (정제 후이므로 실질 정보량은 현재보다 많음)
```

### 개선 후 추출 예시

```html
<!-- fallback 요소 기준 부모 3단계 — 정제 후 -->
<div class="input_wrap">
  <label class="label_txt" for="input01">아이디(이메일계정)</label>
  <input id="input01" type="email" class="input_txt" placeholder="아이디(이메일계정)">
  <span class="error_id">아이디(이메일계정)을 입력해주세요.</span>
</div>
```

---

## 3. HTML 정제 항목

### 제거 대상

| 항목 | 예시 | 제거 이유 |
|---|---|---|
| `<style>` 태그 | CSS 블록 전체 | selector와 무관 |
| `<script>` 태그 | JS 코드 전체 | selector와 무관 |
| `<svg>` 태그 | path, circle 등 | selector와 무관, 매우 장황 |
| `<iframe>` 태그 | 외부 콘텐츠 | selector와 무관 |
| `style` 속성 | `style="margin-top:16px"` | 인라인 CSS, selector에 사용 금지 |
| `data-v-*` 속성 | `data-v-3f8a2b1c` | 빌드 해시, 매 배포마다 변경 |
| 이벤트 핸들러 | `onclick="this.select()"` | JS 핸들러, selector와 무관 |
| `tabindex` | `tabindex="-1"` | selector에 거의 사용 안 함 |
| `aria-hidden` | `aria-hidden="true"` | selector와 무관 |
| `aria-describedby` | `aria-describedby="hint-1"` | selector와 무관 |
| 30자 초과 텍스트 | 약관, 설명 문구 | 앞 30자만 유지 |

### 유지 대상 (selector 생성에 필요)

| 항목 | 예시 | 유지 이유 |
|---|---|---|
| `id` | `id="input01"` | 최우선 selector |
| `class` | `class="input_txt"` | CSS selector |
| `type` | `type="email"` | 입력 필드 구분 |
| `name` | `name="email"` | form 필드 식별 |
| `placeholder` | `placeholder="아이디 입력"` | role= selector에 활용 |
| `role` | `role="button"` | ARIA role selector |
| `aria-label` | `aria-label="닫기"` | role= selector에 활용 |
| `for` | `for="input01"` | label 연결 |
| `href` | `href="/signup"` | 링크 식별 |
| `data-testid` | `data-testid="login-btn"` | 테스트 전용 속성 |
| 짧은 텍스트 | `로그인`, `확인` | role=button[name=...] 에 활용 |

### data-* 속성 처리 기준

```
제거: data-v-[16진수해시] 패턴  →  빌드 툴 자동 생성 (Vue, 등)
유지: data-testid, data-cy, data-test  →  테스트 전용, 안정적
유지: 그 외 data-* → 케이스별 판단, 일단 유지
```

---

## 4. 추출 우선순위 로직

```
_get_element_context(page, fallback_selector=None) 호출
    │
    ├─ fallback_selector 있음?
    │      │
    │      YES → page.locator(fallback_selector).evaluate(부모 3단계 JS)
    │              │
    │              ├─ 성공 → 정제 → 반환
    │              └─ 실패 (JS 오류 등) → 아래 fallback으로
    │
    └─ fallback_selector 없음 or 위 실패
           │
           → page.evaluate(form/main/body 순서 JS)
               │
               └─ 정제 → 최대 4000자 컷 → 반환
```

---

## 5. 구현 코드

### `_get_element_context()` 변경

```python
def _get_element_context(page, fallback_selector: str = None) -> str:
    """
    selector 생성에 필요한 HTML 컨텍스트를 추출하고 정제합니다.

    우선순위:
    1. fallback_selector 있음 → 해당 요소의 부모 3단계 outerHTML (정제)
    2. 없음 or 실패 → form/main/body innerHTML (정제)
    """

    _CLEAN_JS = """
        node => {
            const clone = node.cloneNode(true);

            // 불필요한 태그 전체 제거
            clone.querySelectorAll('script, style, svg, iframe').forEach(n => n.remove());

            clone.querySelectorAll('*').forEach(el => {
                // style 속성 제거
                el.removeAttribute('style');

                // 제거할 속성 목록
                const removeAttrs = ['tabindex', 'aria-hidden', 'aria-describedby'];
                removeAttrs.forEach(attr => el.removeAttribute(attr));

                // 이벤트 핸들러 및 빌드 해시 속성 제거
                Array.from(el.attributes).forEach(attr => {
                    if (
                        attr.name.startsWith('on') ||
                        /^data-v-[a-f0-9]+$/.test(attr.name)
                    ) {
                        el.removeAttribute(attr.name);
                    }
                });

                // 텍스트 노드 30자 초과 시 잘라내기
                // 단, 버튼·링크·레이블은 유지 (name= selector에 사용)
                const keepFullText = ['button', 'a', 'label', 'option'];
                if (!keepFullText.includes(el.tagName.toLowerCase())) {
                    el.childNodes.forEach(child => {
                        if (child.nodeType === Node.TEXT_NODE) {
                            const trimmed = child.textContent.trim();
                            if (trimmed.length > 30) {
                                child.textContent = ' ' + trimmed.substring(0, 30) + '… ';
                            }
                        }
                    });
                }
            });

            return clone.outerHTML;
        }
    """

    # 1순위: fallback 요소 기준 부모 3단계 추출
    if fallback_selector:
        try:
            context = page.locator(fallback_selector).evaluate(f"""
                el => {{
                    let parent = el;
                    for (let i = 0; i < 3; i++) {{
                        if (parent.parentElement) parent = parent.parentElement;
                    }}
                    return ({_CLEAN_JS})(parent);
                }}
            """)
            if context:
                return context[:4000]
        except Exception as e:
            print(f"[Self-Healing] 부모 3단계 추출 실패, fallback으로 전환: {e}")

    # 2순위: form/main/body 순서
    context = page.evaluate(f"""
        () => {{
            const containers = ['form', 'main', '[role=main]', 'body'];
            for (const selector of containers) {{
                const el = document.querySelector(selector);
                if (el) return ({_CLEAN_JS})(el);
            }}
            return ({_CLEAN_JS})(document.body);
        }}
    """)
    return context[:4000]
```

### `try_heal_primary()` 호출부 변경

```python
# 변경 전
element_context = _get_element_context(page)

# 변경 후
element_context = _get_element_context(page, fallback_selector)
```

`heal_locator()`는 fallback 없이 호출되므로 변경 불필요:
```python
# heal_locator() 내부 — 그대로 유지
element_context = _get_element_context(page)  # fallback_selector 없음
```

---

## 6. 실측 결과 (2026-04-04 기준)

대상: `https://accounts.hanatour.com` (로그인 페이지)  
검증 스크립트: `test_context_v2.py`

### 크기 비교

| 경로 | 기존 | v2 | 절감 |
|---|---|---|---|
| form/main/body (fallback 없음) | 4,000자 | 2,435자 | **40%** |
| 부모 3단계 (fallback `#input01`) | 4,000자 | 518자 | **88%** |

### 품질 체크 결과

| 항목 | 결과 |
|---|---|
| `id` 속성 유지 | ✅ |
| `class` 속성 유지 | ✅ |
| `placeholder` 유지 | ✅ |
| `style` 속성 제거 | ✅ |
| `data-v-*` 해시 제거 | ✅ |
| `onclick` 핸들러 제거 | ✅ |
| `<script>` 제거 | ✅ |
| `<svg>` 제거 | ✅ |

### 발견된 수정 사항

`querySelectorAll('*')`은 자식 요소만 순회하고 루트 요소(clone 자신)는 제외합니다.
루트 요소의 `style=""` 속성이 남아있던 문제를 아래와 같이 수정:

```javascript
// 수정 전
clone.querySelectorAll('*').forEach(el => { ... })

// 수정 후
[clone, ...clone.querySelectorAll('*')].forEach(el => { ... })
```

### 기대 효과 (설계 단계 추정)

| 항목 | 현재 | 개선 후 |
|---|---|---|
| 컨텍스트 크기 | 최대 4000자 (고정) | 수백~1000자 수준 (요소 밀도에 따라) |
| 관련성 | 페이지 전체에서 잘라냄 | 실패 요소 주변만 집중 |
| 토큰 비용 | ~1,535 input tokens | 40~60% 절감 기대 |
| selector 정확도 | 무관한 요소 노이즈 포함 | 주변 구조 집중으로 향상 |
| 실제 DOM 영향 | 없음 | 없음 (`cloneNode` 사용) |

---

## 7. 주의사항 및 엣지 케이스

### 버튼·레이블 텍스트 보존
`role=button[name='로그인']` 같은 selector는 텍스트가 정확해야 합니다.
`button`, `a`, `label`, `option` 태그는 텍스트를 자르지 않도록 예외 처리합니다.

### data-testid 보존
`data-v-[해시]` 패턴만 정규식으로 제거하고, `data-testid`, `data-cy` 등은 유지합니다.

```javascript
// 제거: data-v-3f8a2b1c (16진수 해시 패턴)
/^data-v-[a-f0-9]+$/.test(attr.name)

// 유지: data-testid, data-cy, data-test 등
```

### 부모 3단계가 너무 크면?
SPA에서 최상위 `<div id="app">` 같은 컨테이너까지 올라가면 오히려 더 클 수 있습니다.
정제 후에도 4000자 초과 시 컷하는 안전망이 있으므로 문제 없습니다.

### locator.evaluate() 실패 케이스
- `fallback_selector`가 이미 DOM에서 사라진 경우 (네비게이션 후 healing 호출 시)
- Playwright 내부 오류

→ `try/except`로 감싸고 2순위(form/main/body)로 자동 전환합니다.

---

## 8. 변경 범위

| 파일 | 변경 내용 |
|---|---|
| `self_healing.py` | `_get_element_context(page, fallback_selector=None)` 시그니처 변경 + 정제 로직 추가 |
| `self_healing.py` | `try_heal_primary()` 내 호출부: `_get_element_context(page, fallback_selector)` |
| `self_healing.py` | `heal_locator()` 내 호출부: 변경 없음 (fallback_selector 없는 경로) |
| `scripts/base_page.py` | 변경 없음 |
| `locators.json` | 변경 없음 |

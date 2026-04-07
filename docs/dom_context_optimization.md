# DOM Context 최적화

> **상태: ✅ 완료** (2026-04-06)  
> `self_healing.py`의 `_get_element_context()` 개선 설계 및 구현 문서.  
> 검증 도구: `tools/check_context.py`

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

`fallback_selector`로 찾은 요소의 HTML을 정제해 전송하고, 불필요한 속성과 태그를 제거합니다.

### 추출 전략 (우선순위)

```
1순위: fallback_selector 있음
       → [대상 요소]: 요소 자체 outerHTML (정제)
         [주변 구조]: 부모 3단계 outerHTML (정제)
         두 섹션을 합쳐 반환 — AI가 정확히 어떤 요소인지 알면서 구조적 context도 확보

2순위: fallback_selector 없음 (heal_locator 경로)
       → form/main/body 순서로 innerHTML 추출 후 정제

공통: 추출 후 HTML 정제 (style, 해시 속성, 긴 텍스트 등 제거)
      → 최대 4000자 컷 (정제 후이므로 실질 정보량은 현재보다 많음)
```

### 설계 배경: 1+2 접근 채택 이유

초기 설계는 부모 3단계만 전달하는 방식이었으나, 실측에서 형제 요소(비밀번호 입력 필드 등)를 잘못된 후보로 제안하는 문제가 발견됐습니다.

두 가지 방안을 검토했습니다:

| 방안 | 혼동 차단 | 부작용 |
|---|---|---|
| 요소 자체 HTML만 전달 | 완전 차단 | 부모 구조 없어 구조적 selector 품질 저하 |
| 요소 + 주변 구조 분리 섹션 | 완전 차단 | 토큰 소폭 증가 (부모만 전달 대비) |

`[대상 요소]` / `[주변 구조]` 두 섹션으로 분리해 전달하는 방식을 채택했습니다.
프롬프트에서 "[대상 요소]의 selector만 제안하세요"로 명시해 AI 혼동을 원천 차단합니다.

### 개선 후 추출 예시

```
[대상 요소]
<input id="input01" type="email" placeholder="hana@hanatour.com">

[주변 구조]
<div class="inner_cont">
  <span class="input_text">
    <input id="input01" type="email" placeholder="hana@hanatour.com">
    <label for="input01">아이디(이메일계정)</label>
  </span>
  <span class="input_text">
    <input id="input02" type="password">
    <label for="input02">비밀번호</label>
  </span>
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
    │      YES → page.locator(fallback_selector).evaluate(JS)
    │              │  ├─ el 자체 outerHTML 정제 → [대상 요소]
    │              │  └─ 부모 3단계 outerHTML 정제 → [주변 구조]
    │              │
    │              ├─ 성공 → "[대상 요소]\n...\n\n[주변 구조]\n..." 반환
    │              └─ 실패 (JS 오류 등) → 아래 경로로
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

    fallback_selector 있음:
      [대상 요소] 섹션에 요소 자체 outerHTML,
      [주변 구조] 섹션에 부모 3단계 outerHTML을 합쳐 반환.
    fallback_selector 없음 or 실패:
      form/main/body innerHTML (정제) 반환.
    """

    _CLEAN_JS = """
        node => {
            const clone = node.cloneNode(true);

            clone.querySelectorAll('script, style, svg, iframe').forEach(n => n.remove());

            // 루트 요소 자체 + 모든 자식 요소 정제
            [clone, ...clone.querySelectorAll('*')].forEach(el => {
                el.removeAttribute('style');

                ['tabindex', 'aria-hidden', 'aria-describedby'].forEach(attr => {
                    el.removeAttribute(attr);
                });

                Array.from(el.attributes).forEach(attr => {
                    if (
                        attr.name.startsWith('on') ||
                        /^data-v-[a-f0-9]+$/.test(attr.name)
                    ) {
                        el.removeAttribute(attr.name);
                    }
                });

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

    # 1순위: 요소 자체 + 부모 3단계 구조를 분리 섹션으로 반환
    if fallback_selector:
        try:
            el_html, parent_html = page.locator(fallback_selector).evaluate(f"""
                el => {{
                    const elHtml = ({_CLEAN_JS})(el);

                    let parent = el;
                    for (let i = 0; i < 3; i++) {{
                        if (parent.parentElement) parent = parent.parentElement;
                    }}
                    const parentHtml = ({_CLEAN_JS})(parent);

                    return [elHtml, parentHtml];
                }}
            """)
            if el_html:
                context = f"[대상 요소]\n{el_html}\n\n[주변 구조]\n{parent_html}"
                return context[:4000]
        except Exception as e:
            print(f"[Self-Healing] 요소 추출 실패, form/main/body로 전환: {e}")

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

### `try_heal_primary()` 프롬프트 변경

```python
# 변경 전
f"fallback으로 찾은 selector: {fallback_selector}\n"
f"찾으려는 요소: {section} 섹션의 {key}\n\n"
f"현재 DOM:\n{element_context}\n\n"
"DOM에서 이 요소에 적합한 안정적인 Playwright selector를 반드시 3개 찾아 제안해주세요."

# 변경 후
f"찾으려는 요소: {section} 섹션의 {key}\n\n"
f"아래 DOM에서 [대상 요소]가 바로 찾으려는 요소입니다.\n"
f"[대상 요소]의 selector만 제안하세요. 다른 요소의 selector는 절대 포함하지 마세요.\n\n"
f"{element_context}\n\n"
"위 [대상 요소]에 적합한 안정적인 Playwright selector를 반드시 3개 찾아 제안해주세요."
```

`heal_locator()`는 fallback 없이 호출되므로 변경 불필요:
```python
# heal_locator() 내부 — 그대로 유지
element_context = _get_element_context(page)  # fallback_selector 없음
```

---

## 6. 실측 결과

대상: 로그인 페이지  
검증 스크립트: `tools/check_context.py`

### 컨텍스트 크기 비교 (2026-04-04)

| 경로 | 기존 | 개선 후 | 절감 |
|---|---|---|---|
| form/main/body (fallback 없음) | 4,000자 | 2,435자 | **40%** |
| 요소+주변구조 (fallback `role=textbox[...]`) | 4,000자 | 477자 | **88%** |

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

### OpenAI 호출 비교 (2026-04-06)

조건: `email_input` 요소, failed=`#input03`, fallback=`role=textbox[name='아이디(이메일계정)']`

| | 기존 (v1) | 개선 후 |
|---|---|---|
| input tokens | 1,686 | 477 |
| 1순위 | `#input01` ✅ | `#input01` ✅ |
| 2순위 | `role=textbox[name='아이디(이메일계정)']` ✅ | `role=textbox[name='아이디(이메일계정)']` ✅ |
| 3순위 | `role=textbox[name='비밀번호']` ❌ | `.input_text input[type='email']` ✅ |

3순위에서 다른 요소(비밀번호 필드) selector가 제거되고 올바른 후보로 교체됨.

### 발견된 수정 사항 (2026-04-04)

`querySelectorAll('*')`은 자식 요소만 순회하고 루트 요소(clone 자신)는 제외합니다.
루트 요소의 `style=""` 속성이 남아있던 문제를 아래와 같이 수정:

```javascript
// 수정 전
clone.querySelectorAll('*').forEach(el => { ... })

// 수정 후
[clone, ...clone.querySelectorAll('*')].forEach(el => { ... })
```

### 실측 효과 요약

| 항목 | 기존 | 개선 후 |
|---|---|---|
| 컨텍스트 크기 | 최대 4,000자 (고정) | 477자 수준 (요소 밀도에 따라) |
| input tokens | ~1,686 | ~477 (**72% 절감**) |
| selector 정확도 | 무관한 요소 노이즈 포함 | 대상 요소 집중, 오답 제거 |
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
| `self_healing.py` | `try_heal_primary()` 호출부: `_get_element_context(page, fallback_selector)` |
| `self_healing.py` | `try_heal_primary()` 프롬프트: `[대상 요소]` 명시 및 다른 요소 제안 금지 문구 추가 |
| `self_healing.py` | `heal_locator()` 내 호출부: 변경 없음 (fallback_selector 없는 경로) |
| `scripts/base_page.py` | 변경 없음 |
| `locators.json` | 변경 없음 |

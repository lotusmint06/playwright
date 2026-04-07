"""
Locator 사전 생성 도구 (웹 전용 — Playwright)

테스트 실패를 기다리지 않고 사전에 locators.json에 selector를 등록한다.
OPENAI_API_KEY 환경변수가 필요하다.

사용법:
    python tools/generate_locator.py \\
        --url https://example.com/login \\
        --section login \\
        --key email_input \\
        --description "이메일 입력 필드"

결과:
    locators.json의 [section][key]에 primary + fallback 자동 등록
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# 프로젝트 루트를 경로에 추가해 self_healing 모듈 import 가능하게 함
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from self_healing import _get_element_context, client  # noqa: E402

LOCATORS_FILE = "locators.json"


def _get_page_context(page, description: str = "") -> str:
    """description 키워드로 관련 요소를 먼저 탐색하고, 없으면 _get_element_context 폴백."""
    if not description:
        return _get_element_context(page)

    # 설명의 각 단어를 순서대로 시도해 첫 번째 매칭 키워드 사용
    keyword = None
    for word in description.split():
        if len(word) >= 2:  # 1글자 단어(조사 등) 스킵
            keyword = word
            break
    if not keyword:
        return _get_element_context(page)

    # self_healing._get_element_context의 _CLEAN_JS와 동일한 정제 로직
    _CLEAN_JS = """
        node => {
            const clone = node.cloneNode(true);
            clone.querySelectorAll('script, style, svg, iframe').forEach(n => n.remove());
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

    focused = page.evaluate(f"""
        (keyword) => {{
            const clean = {_CLEAN_JS};
            const candidates = document.querySelectorAll('a, button, input, [role=button], [role=link]');
            const matches = [];
            for (const el of candidates) {{
                const text = (el.textContent || '').trim();
                const aria = el.getAttribute('aria-label') || '';
                const placeholder = el.getAttribute('placeholder') || '';
                const title = el.getAttribute('title') || '';
                if (text.includes(keyword) || aria.includes(keyword)
                        || placeholder.includes(keyword) || title.includes(keyword)) {{
                    const elHtml = clean(el);
                    let parent = el;
                    for (let i = 0; i < 3; i++) {{
                        if (parent.parentElement) parent = parent.parentElement;
                    }}
                    const parentHtml = clean(parent);
                    matches.push('[대상 요소]\\n' + elHtml + '\\n\\n[주변 구조]\\n' + parentHtml);
                }}
            }}
            return matches.slice(0, 3).join('\\n\\n---\\n\\n') || null;
        }}
    """, keyword)

    if focused:
        print(f"[Context] 키워드 '{keyword}' 매칭 요소 추출 완료")
        return focused[:4000]

    print(f"[Context] 키워드 '{keyword}' 매칭 없음 — form/main/body로 전환")
    return _get_element_context(page)


def _ask_openai(description: str, context: str) -> list[str]:
    """self_healing.py의 client와 동일한 프롬프트 구조로 selector 후보 3개 요청."""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a Playwright test automation expert. Respond only with valid JSON.",
            },
            {
                "role": "user",
                "content": (
                    f"찾으려는 요소: {description}\n\n"
                    f"아래 DOM에서 [대상 요소]가 바로 찾으려는 요소입니다.\n"
                    f"[대상 요소]의 selector만 제안하세요. 다른 요소의 selector는 절대 포함하지 마세요.\n\n"
                    f"{context}\n\n"
                    "위 [대상 요소]에 적합한 안정적인 Playwright selector를 반드시 3개 찾아 제안해주세요. 3개 미만은 허용하지 않습니다.\n"
                    "우선순위: #id > role=link[name=...] > role=button[name=...] > role=textbox[name=...] > text=텍스트 > css(정적 class) 순으로 우선합니다.\n"
                    "<a> 태그는 role=link[name=...] 또는 text=텍스트 로 표현하세요. role=button 으로 표현하지 마세요.\n"
                    "#id가 존재하면 반드시 첫 번째 후보로 제안하세요.\n"
                    "data-v-*, data-v6-, data-* 등 빌드 툴이 자동 생성하는 속성은 절대 사용하지 마세요.\n"
                    "disable, active, focus, hover, selected, checked 등 상태에 따라 동적으로 변하는 class는 포함하지 마세요.\n"
                    ":has-text() 구문은 사용하지 마세요. 대신 text=텍스트 또는 role=link[name='텍스트'] 를 사용하세요.\n"
                    "selector 문법: role=link[name='텍스트'], text=텍스트, #id, .static-class (css= prefix 사용 금지)\n"
                    '응답 형식: {"selectors": ["...", "...", "..."]}'
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(res.choices[0].message.content)
    return data.get("selectors", [])


def _validate_candidates(page, candidates: list[str]) -> tuple[str | None, list[str]]:
    """후보 selector를 순서대로 검증해 primary와 나머지 fallback 반환."""
    primary = None
    fallback = []

    for sel in candidates:
        try:
            page.locator(sel).wait_for(state="attached", timeout=3000)
            if primary is None:
                primary = sel
                print(f"  [✅] primary: {sel}")
            else:
                fallback.append(sel)
                print(f"  [✅] fallback: {sel}")
        except Exception:
            print(f"  [❌] 실패: {sel}")

    return primary, fallback


def _update_locators(section: str, key: str, primary: str, fallback: list[str]):
    """locators.json에 section/key 등록 또는 갱신."""
    if os.path.exists(LOCATORS_FILE):
        with open(LOCATORS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data.setdefault(section, {})
    data[section][key] = {
        "primary": primary,
        "fallback": fallback if fallback else None,
        "previous": None,
        "healed": False,
    }

    with open(LOCATORS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] locators.json [{section}][{key}] 등록됨")
    print(f"  primary : {primary}")
    print(f"  fallback: {fallback}")


def main():
    parser = argparse.ArgumentParser(description="Locator 사전 생성 도구 (웹 전용)")
    parser.add_argument("--url", required=True, help="대상 페이지 URL")
    parser.add_argument("--section", required=True, help="locators.json 섹션명")
    parser.add_argument("--key", required=True, help="locators.json 키명")
    parser.add_argument("--description", required=True, help="찾으려는 요소 설명 (예: '로그인 버튼')")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("[오류] OPENAI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    print(f"[1/4] 페이지 접속: {args.url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(args.url)

        print("[2/4] DOM 컨텍스트 추출 중...")
        context = _get_page_context(page, args.description)

        print("[3/4] OpenAI에 selector 후보 요청 중...")
        candidates = _ask_openai(args.description, context)
        print(f"  후보: {candidates}")

        print("[4/4] 후보 검증 중...")
        primary, fallback = _validate_candidates(page, candidates)
        browser.close()

    if not primary:
        print("\n[실패] 유효한 selector를 찾지 못했습니다. --description을 더 구체적으로 작성해보세요.")
        sys.exit(1)

    _update_locators(args.section, args.key, primary, fallback)


if __name__ == "__main__":
    main()

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

load_dotenv()

LOCATORS_FILE = "locators.json"


def _get_page_context(page) -> str:
    """DOM에서 selector 생성에 필요한 HTML 추출 및 정제."""
    _CLEAN_JS = """
        node => {
            const clone = node.cloneNode(true);
            clone.querySelectorAll('script, style, svg, iframe').forEach(n => n.remove());
            [clone, ...clone.querySelectorAll('*')].forEach(el => {
                el.removeAttribute('style');
                ['tabindex', 'aria-hidden', 'aria-describedby'].forEach(a => el.removeAttribute(a));
                Array.from(el.attributes).forEach(attr => {
                    if (attr.name.startsWith('on') || /^data-v-[a-f0-9]+$/.test(attr.name)) {
                        el.removeAttribute(attr.name);
                    }
                });
            });
            return clone.outerHTML;
        }
    """
    context = page.evaluate(f"""
        () => {{
            const containers = ['form', 'main', '[role=main]', 'body'];
            for (const sel of containers) {{
                const el = document.querySelector(sel);
                if (el) return ({_CLEAN_JS})(el);
            }}
            return ({_CLEAN_JS})(document.body);
        }}
    """)
    return context[:4000]


def _ask_openai(description: str, context: str) -> list[str]:
    """OpenAI에 selector 후보 3개 요청."""
    from openai import OpenAI
    client = OpenAI()

    prompt = (
        f"찾으려는 요소: {description}\n\n"
        f"아래 DOM에서 해당 요소에 적합한 안정적인 Playwright selector를 3개 제안해주세요.\n"
        f"반드시 JSON 형식으로만 응답하세요: {{\"selectors\": [\"...\", \"...\", \"...\"]}}\n\n"
        f"{context}"
    )

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = res.choices[0].message.content.strip()
    data = json.loads(raw)
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
        page.goto(args.url, wait_until="networkidle")

        print("[2/4] DOM 컨텍스트 추출 중...")
        context = _get_page_context(page)

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

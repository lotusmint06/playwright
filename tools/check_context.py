"""
_get_element_context() 검증 스크립트

DOM 컨텍스트 추출 결과를 확인하고, OpenAI를 통한 selector 후보 품질을 검증합니다.

실행:
    python tools/check_context.py                     # form/main/body 경로
    python tools/check_context.py --preset email      # email_input 프리셋 (fallback 경로)
    python tools/check_context.py --preset email --openai   # OpenAI 호출 포함
"""

import argparse
import json
import os
os.environ.setdefault("OPENAI_API_KEY", "dummy-for-context-test")  # 모듈 로드용, OpenAI 호출 없음

from playwright.sync_api import sync_playwright
from self_healing import _get_element_context

TARGET_URL = "https://accounts.hanatour.com"


def _call_openai(context: str, section: str, key: str, failed_selector: str) -> list[str]:
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a Playwright test automation expert. Respond only with valid JSON."
            },
            {
                "role": "user",
                "content": (
                    f"기존 primary selector가 변경되었습니다: {failed_selector}\n"
                    f"찾으려는 요소: {section} 섹션의 {key}\n\n"
                    f"아래 DOM에서 [대상 요소]가 바로 찾으려는 요소입니다.\n"
                    f"[대상 요소]의 selector만 제안하세요. 다른 요소의 selector는 절대 포함하지 마세요.\n\n"
                    f"{context}\n\n"
                    "위 [대상 요소]에 적합한 안정적인 Playwright selector를 반드시 3개 찾아 제안해주세요. 3개 미만은 허용하지 않습니다.\n"
                    "우선순위: #id > role=button[name=...] > role=textbox[name=...] > css(정적 class) 순으로 우선합니다.\n"
                    "#id가 존재하면 반드시 첫 번째 후보로 제안하세요.\n"
                    "data-v-*, data-v6-, data-* 등 빌드 툴이 자동 생성하는 속성은 절대 사용하지 마세요.\n"
                    "disable, active, focus, hover, selected, checked 등 상태에 따라 동적으로 변하는 class는 포함하지 마세요.\n"
                    "selector 문법: role=button[name='텍스트'], #id, .static-class (css= prefix 사용 금지)\n"
                    '응답 형식: {"selectors": ["...", "...", "..."]}'
                )
            }
        ],
        response_format={"type": "json_object"}
    )
    usage = response.usage
    print(f"  토큰 — input: {usage.prompt_tokens}, output: {usage.completion_tokens}, total: {usage.total_tokens}")
    return json.loads(response.choices[0].message.content).get("selectors", [])


def compare(fallback_selector: str = None, openai: bool = False,
            section: str = None, key: str = None, failed_selector: str = None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(TARGET_URL)
        page.wait_for_load_state("networkidle")

        print("=" * 60)
        print(f"대상 URL : {TARGET_URL}")
        print(f"fallback : {fallback_selector or '없음 (form/main/body 경로)'}")
        print("=" * 60)

        # 기존 방식
        ctx_v1 = _get_element_context(page)
        print(f"\n[기존] 크기: {len(ctx_v1)}자")
        print("-" * 40)
        print(ctx_v1[:500], "..." if len(ctx_v1) > 500 else "")

        print()

        # 신규 방식
        ctx_v2 = _get_element_context(page, fallback_selector)
        print(f"\n[v2]   크기: {len(ctx_v2)}자  (절감: {len(ctx_v1) - len(ctx_v2)}자 / {100 - int(len(ctx_v2)/len(ctx_v1)*100)}%)")
        print("-" * 40)
        print(ctx_v2[:500], "..." if len(ctx_v2) > 500 else "")

        # 품질 체크: selector 생성에 필요한 속성이 유지됐는지 확인
        print("\n[품질 체크]")
        checks = {
            "id 속성 유지":          'id="'          in ctx_v2,
            "class 속성 유지":       'class="'       in ctx_v2,
            "placeholder 유지":      'placeholder'   in ctx_v2,
            "style 속성 제거":       'style="'       not in ctx_v2,
            "data-v-* 해시 제거":    'data-v-'       not in ctx_v2,
            "onclick 핸들러 제거":   'onclick'       not in ctx_v2,
            "<script> 제거":         '<script'       not in ctx_v2,
            "<svg> 제거":            '<svg'          not in ctx_v2,
        }
        all_pass = True
        for label, result in checks.items():
            mark = "✅" if result else "❌"
            print(f"  {mark} {label}")
            if not result:
                all_pass = False

        print()
        print("=" * 60)
        print("결과:", "전체 통과 ✅" if all_pass else "일부 실패 ❌ — 위 항목 확인 필요")
        print("=" * 60)

        # OpenAI 비교
        if openai:
            if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "dummy-for-context-test":
                print("\n⚠️  OPENAI_API_KEY가 설정되지 않아 OpenAI 호출을 건너뜁니다.")
            else:
                print(f"\n{'=' * 60}")
                print(f"[OpenAI 비교]  section={section}, key={key}, failed={failed_selector}")
                print("=" * 60)

                print("\n[기존 v1 컨텍스트 → OpenAI]")
                candidates_v1 = _call_openai(ctx_v1, section, key, failed_selector)
                for i, c in enumerate(candidates_v1, 1):
                    print(f"  {i}순위: {c}")

                print("\n[v2 컨텍스트 → OpenAI]")
                candidates_v2 = _call_openai(ctx_v2, section, key, failed_selector)
                for i, c in enumerate(candidates_v2, 1):
                    print(f"  {i}순위: {c}")

                print("\n[결과 비교]")
                same = set(candidates_v1) == set(candidates_v2)
                print(f"  동일 여부: {'✅ 동일' if same else '⚠️  다름'}")
                if not same:
                    only_v1 = set(candidates_v1) - set(candidates_v2)
                    only_v2 = set(candidates_v2) - set(candidates_v1)
                    if only_v1:
                        print(f"  v1에만 있음: {list(only_v1)}")
                    if only_v2:
                        print(f"  v2에만 있음: {list(only_v2)}")

        browser.close()


PRESETS = {
    "email": {
        "selector": "role=textbox[name='아이디(이메일계정)']",
        "section":  "login",
        "key":      "email_input",
        "failed":   "#input03",
    },
    "submit": {
        "selector": None,
        "section":  "login",
        "key":      "submit_btn",
        "failed":   "css=.btn_old",
    },
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--selector", default=None,           help="fallback selector")
    parser.add_argument("--openai",   action="store_true",    help="OpenAI 호출 비교 활성화")
    parser.add_argument("--section",  default="login",        help="locator 섹션명")
    parser.add_argument("--key",      default="submit_btn",   help="locator 키명")
    parser.add_argument("--failed",   default="css=.btn_login_submit", help="실패한 selector")
    parser.add_argument("--preset",   choices=PRESETS.keys(), help="사전 정의된 테스트 케이스")
    args = parser.parse_args()

    if args.preset:
        p = PRESETS[args.preset]
        compare(p["selector"], args.openai, p["section"], p["key"], p["failed"])
    else:
        compare(args.selector, args.openai, args.section, args.key, args.failed)

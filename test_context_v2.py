"""
_get_element_context_v2() 검증 스크립트

기존 _get_element_context()와 결과를 나란히 비교합니다.

실행:
    python test_context_v2.py
    python test_context_v2.py --selector "#input01"   # fallback selector 지정
"""

import argparse
import os
os.environ.setdefault("OPENAI_API_KEY", "dummy-for-context-test")  # 모듈 로드용, OpenAI 호출 없음

from playwright.sync_api import sync_playwright
from self_healing import _get_element_context, _get_element_context_v2

TARGET_URL = "https://accounts.hanatour.com"


def compare(fallback_selector: str = None):
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
        ctx_v2 = _get_element_context_v2(page, fallback_selector)
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

        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--selector", default=None, help="fallback selector (예: '#input01')")
    args = parser.parse_args()
    compare(args.selector)

"""
OpenAI(gpt-4o-mini) 기반 Self-Healing Locator

selector 실패 시 현재 DOM을 분석해 새 selector를 제안하고
locators.json을 자동 업데이트합니다.

제한:
- 동일 요소에 최대 3회 healing 시도 (.heal_count.json)
- healing 성공 시 healed: true 플래그 기록 → PR 전 수동 검토 필요
"""

import json
import os
from openai import OpenAI

HEAL_COUNT_FILE = ".heal_count.json"
MAX_HEAL_COUNT = 3

client = OpenAI()  # OPENAI_API_KEY 환경변수에서 자동으로 읽음


def _load_heal_counts() -> dict:
    if not os.path.exists(HEAL_COUNT_FILE):
        return {}
    with open(HEAL_COUNT_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_heal_counts(counts: dict):
    with open(HEAL_COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f, ensure_ascii=False, indent=2)


def _get_element_context(page) -> str:
    """전체 DOM 대신 주요 컨테이너 내부만 추출해 토큰 절약"""
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


def heal_locator(page, section: str, key: str, failed_selector: str) -> list[str]:
    """OpenAI에 DOM 분석을 요청하고 새 selector 후보를 반환합니다."""
    element_context = _get_element_context(page)

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
                    f"다음 Playwright selector가 실패했습니다: {failed_selector}\n"
                    f"찾으려는 요소: {section} 섹션의 {key}\n\n"
                    f"현재 DOM:\n{element_context}\n\n"
                    "Playwright에서 사용 가능한 selector를 안정성 순으로 최대 3개 제안해주세요. 확실하지 않은 selector는 포함하지 마세요.\n"
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

    result = json.loads(response.choices[0].message.content)
    return result.get("selectors", [])


def _update_locator_json(section: str, key: str, new_selector: str, old_selector: str, extra_fallbacks: list[str] = None):
    with open("locators.json", encoding="utf-8") as f:
        locators = json.load(f)

    entry = locators[section][key]
    entry["previous"] = old_selector
    entry["primary"] = new_selector
    entry["healed"] = True

    if extra_fallbacks:
        existing = entry.get("fallback") or []
        if isinstance(existing, str):
            existing = [existing]
        # extra_fallbacks 내부 중복 제거 후 기존 fallback과 합치기
        seen = set()
        deduped = [f for f in extra_fallbacks if not (f in seen or seen.add(f))]
        merged = deduped + [f for f in existing if f not in seen and f != new_selector]
        entry["fallback"] = merged
        print(f"[Self-Healing] fallback 업데이트 → {merged}")

    with open("locators.json", "w", encoding="utf-8") as f:
        json.dump(locators, f, ensure_ascii=False, indent=2)


def try_heal_primary(page, section: str, key: str, failed_primary: str, fallback_selector: str) -> bool:
    """
    fallback으로 요소를 찾은 뒤 호출됩니다.
    OpenAI에게 DOM 기반으로 새 primary(id/css) selector를 제안받아 업데이트합니다.
    성공 시 True, 실패 시 False 반환.
    """
    full_key = f"{section}.{key}"
    counts = _load_heal_counts()

    if counts.get(full_key, 0) >= MAX_HEAL_COUNT:
        print(f"[Self-Healing] {full_key} — healing {MAX_HEAL_COUNT}회 초과. 수동 확인 필요")
        return False

    print(f"[Self-Healing] {full_key}: fallback 성공 → OpenAI로 새 primary 탐색")
    element_context = _get_element_context(page)

    # 전체 primary + 같은 섹션 내 fallback 수집 (다른 섹션은 같은 selector 허용)
    with open("locators.json", encoding="utf-8") as f:
        all_locators = json.load(f)
    used_selectors = []
    for sec_name, sec in all_locators.items():
        for v in sec.values():
            if not isinstance(v, dict):
                continue
            if v.get("primary"):
                used_selectors.append(v["primary"])
            if sec_name == section:
                fb = v.get("fallback") or []
                if isinstance(fb, str):
                    fb = [fb]
                used_selectors.extend(fb)

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
                    f"기존 primary selector가 변경되었습니다: {failed_primary}\n"
                    f"fallback으로 찾은 selector: {fallback_selector}\n"
                    f"찾으려는 요소: {section} 섹션의 {key}\n\n"
                    f"현재 DOM:\n{element_context}\n\n"
                    "DOM에서 이 요소에 적합한 안정적인 Playwright selector를 반드시 3개 찾아 제안해주세요. 3개 미만은 허용하지 않습니다.\n"
                    "fallback selector는 참고용이며, 더 안정적인 새 selector를 DOM에서 직접 찾아야 합니다.\n"
                    "우선순위: #id > role=button[name=...] > role=textbox[name=...] > css(정적 class) 순으로 우선합니다.\n"
                    "#id가 존재하면 반드시 첫 번째 후보로 제안하세요.\n"
                    "data-v-*, data-v6-, data-* 등 빌드 툴이 자동 생성하는 속성은 절대 사용하지 마세요.\n"
                    "disable, active, focus, hover, selected, checked 등 상태에 따라 동적으로 변하는 class는 포함하지 마세요.\n"
                    "selector 문법: role=button[name='텍스트'], #id, .static-class (css= prefix 사용 금지)\n"
                    f"아래 selector는 이미 다른 요소에 사용 중이므로 제안하지 마세요:\n{used_selectors}\n\n"
                    '응답 형식: {"selectors": ["#new-id", "role=...", "..."]}'
                )
            }
        ],
        response_format={"type": "json_object"}
    )

    usage = response.usage
    print(
        f"[Self-Healing] 토큰 사용량 — "
        f"input: {usage.prompt_tokens}, "
        f"output: {usage.completion_tokens}, "
        f"total: {usage.total_tokens}"
    )

    candidates = json.loads(response.choices[0].message.content).get("selectors", [])

    for i, c in enumerate(candidates, 1):
        print(f"[Self-Healing] AI 후보 {i}순위: {c}")

    for i, candidate in enumerate(candidates):
        try:
            locator = page.locator(candidate)
            locator.wait_for(timeout=2000)

            extra_fallbacks = [c for c in candidates[i + 1:] if c != candidate]
            _update_locator_json(section, key, candidate, failed_primary, extra_fallbacks)
            counts[full_key] = counts.get(full_key, 0) + 1
            _save_heal_counts(counts)

            print(f"[Self-Healing] ✅ {full_key} 새 primary 업데이트: {candidate}")
            print(f"[Self-Healing] ⚠️  locators.json 업데이트됨 — PR 전 수동 검토 필요")
            return True

        except Exception:
            continue

    counts[full_key] = counts.get(full_key, 0) + 1
    _save_heal_counts(counts)
    print(f"[Self-Healing] {full_key} — 새 primary 후보 모두 실패: {candidates}")
    return False


def try_heal(page, section: str, key: str, failed_selector: str):
    """
    healing을 시도하고 성공한 Playwright locator 객체를 반환합니다.
    healing 횟수 초과 또는 모든 후보 실패 시 Exception을 발생시킵니다.
    """
    full_key = f"{section}.{key}"
    counts = _load_heal_counts()

    if counts.get(full_key, 0) >= MAX_HEAL_COUNT:
        raise Exception(
            f"[Self-Healing] {full_key} — healing {MAX_HEAL_COUNT}회 초과. 수동 확인이 필요합니다."
        )

    print(f"[Self-Healing] {full_key} 실패 → OpenAI로 healing 시도")
    candidates = heal_locator(page, section, key, failed_selector)

    for i, candidate in enumerate(candidates):
        try:
            locator = page.locator(candidate)
            locator.wait_for(timeout=2000)

            extra_fallbacks = [c for c in candidates[i + 1:] if c != candidate]
            _update_locator_json(section, key, candidate, failed_selector, extra_fallbacks)
            counts[full_key] = counts.get(full_key, 0) + 1
            _save_heal_counts(counts)

            print(f"[Self-Healing] ✅ {full_key} 복구 성공: {candidate}")
            print(f"[Self-Healing] ⚠️  locators.json 업데이트됨 — PR 전 수동 검토 필요")
            return locator

        except Exception:
            continue

    counts[full_key] = counts.get(full_key, 0) + 1
    _save_heal_counts(counts)
    raise Exception(f"[Self-Healing] {full_key} — 모든 후보 실패: {candidates}")

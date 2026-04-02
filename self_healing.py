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
                    "Playwright에서 사용 가능한 selector를 안정성 순으로 3개 제안해주세요.\n"
                    "get_by_role, get_by_text, css 순으로 우선합니다.\n"
                    '응답 형식: {"selectors": ["...", "...", "..."]}'
                )
            }
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    return result.get("selectors", [])


def _update_locator_json(section: str, key: str, new_selector: str, old_selector: str):
    with open("locators.json", encoding="utf-8") as f:
        locators = json.load(f)

    locators[section][key]["previous"] = old_selector
    locators[section][key]["primary"] = new_selector
    locators[section][key]["healed"] = True

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

    # 현재 locators.json에서 사용 중인 모든 primary selector 수집
    with open("locators.json", encoding="utf-8") as f:
        all_locators = json.load(f)
    used_selectors = [
        v["primary"]
        for sec in all_locators.values()
        for v in sec.values()
        if isinstance(v, dict) and v.get("primary")
    ]

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
                    "DOM에서 이 요소에 적합한 안정적인 Playwright selector를 찾아 새 primary로 제안해주세요.\n"
                    "우선순위: role=button[name=...] > role=textbox[name=...] > #id > data-* > css class 순으로 우선합니다.\n"
                    "버튼이나 링크처럼 텍스트가 있는 요소는 반드시 role 기반 selector를 첫 번째로 제안하세요.\n"
                    "주의: disable, active, focus, hover, selected, checked 등 상태에 따라 동적으로 변하는 class는 포함하지 마세요.\n"
                    f"아래 selector는 이미 다른 요소에 사용 중이므로 제안하지 마세요:\n{used_selectors}\n\n"
                    '응답 형식: {"selectors": ["#new-id", "css=...", "..."]}'
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

    for candidate in candidates:
        try:
            locator = page.locator(candidate)
            locator.wait_for(timeout=2000)

            _update_locator_json(section, key, candidate, failed_primary)
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

    for candidate in candidates:
        try:
            locator = page.locator(candidate)
            locator.wait_for(timeout=2000)

            _update_locator_json(section, key, candidate, failed_selector)
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

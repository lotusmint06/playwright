"""
OpenAI(gpt-4o-mini) 기반 앱 Self-Healing Locator (Appium)

selector 실패 시 현재 XML UI 계층을 분석해 새 selector를 제안하고
app_locators.json을 자동 업데이트합니다.

제한:
- 동일 요소에 최대 3회 healing 시도 (.app_heal_count.json)
- healing 성공 시 healed: true 플래그 기록 → PR 전 수동 검토 필요
"""

import json
import os
import re
import xml.etree.ElementTree as ET
from openai import OpenAI
from appium.webdriver.common.appiumby import AppiumBy

HEAL_COUNT_FILE = ".app_heal_count.json"
MAX_HEAL_COUNT = 3

client = OpenAI()


def _load_heal_counts() -> dict:
    if not os.path.exists(HEAL_COUNT_FILE):
        return {}
    with open(HEAL_COUNT_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_heal_counts(counts: dict):
    with open(HEAL_COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f, ensure_ascii=False, indent=2)


def _parse_appium_selector(selector: str):
    if selector.startswith("accessibility_id:"):
        return AppiumBy.ACCESSIBILITY_ID, selector[len("accessibility_id:"):]
    elif selector.startswith("xpath:"):
        return AppiumBy.XPATH, selector[len("xpath:"):]
    elif selector.startswith("id:"):
        return AppiumBy.ID, selector[len("id:"):]
    elif selector.startswith("uiautomator:"):
        return AppiumBy.ANDROID_UIAUTOMATOR, selector[len("uiautomator:"):]
    return AppiumBy.XPATH, selector


def _get_xml_context(driver, fallback_selector: str = None) -> str:
    """
    현재 화면의 XML UI 계층에서 컨텍스트를 추출합니다.

    fallback_selector 있음:
      [대상 요소] 섹션에 요소 자체 XML,
      [주변 구조] 섹션에 부모 3단계 XML을 합쳐 반환.
    fallback_selector 없음 or 실패:
      전체 page_source XML 반환 (4000자 제한).
    """
    page_source = driver.page_source

    if fallback_selector:
        try:
            by, value = _parse_appium_selector(fallback_selector)
            root = ET.fromstring(page_source)

            # 요소 탐색
            target = None
            if by == AppiumBy.ACCESSIBILITY_ID:
                target = root.find(f".//*[@content-desc='{value}']")
            elif by == AppiumBy.ID:
                target = root.find(f".//*[@resource-id='{value}']")
            elif by == AppiumBy.XPATH:
                # xpath 표현식에서 content-desc 또는 resource-id 값 추출 후 탐색
                m = re.search(r"@content-desc='([^']+)'", value)
                if m:
                    target = root.find(f".//*[@content-desc='{m.group(1)}']")
                if target is None:
                    m = re.search(r"@resource-id='([^']+)'", value)
                    if m:
                        target = root.find(f".//*[@resource-id='{m.group(1)}']")
            elif by == AppiumBy.ANDROID_UIAUTOMATOR:
                # new UiSelector().description("value") → content-desc로 탐색
                m = re.search(r'description\("([^"]+)"\)', value)
                if m:
                    target = root.find(f".//*[@content-desc='{m.group(1)}']")
                # resourceId("value") → resource-id로 탐색
                if target is None:
                    m = re.search(r'resourceId\("([^"]+)"\)', value)
                    if m:
                        target = root.find(f".//*[@resource-id='{m.group(1)}']")

            if target is not None:
                el_xml = ET.tostring(target, encoding="unicode")

                # 부모 3단계 탐색 (ET는 부모 참조 없으므로 parent map 사용)
                parent_map = {child: parent for parent in root.iter() for child in parent}
                parent = target
                for _ in range(3):
                    parent = parent_map.get(parent, parent)
                parent_xml = ET.tostring(parent, encoding="unicode")

                context = f"[대상 요소]\n{el_xml}\n\n[주변 구조]\n{parent_xml}"
                print(f"[Context-App] 대상 요소({len(el_xml)}자) + 주변 구조({len(parent_xml)}자) 추출 완료")
                return context[:4000]
        except Exception as e:
            print(f"[Context-App] 요소 추출 실패, 전체 XML로 전환: {e}")

    print(f"[Context-App] 전체 XML 추출 완료 ({len(page_source)}자)")
    return page_source[:4000]


def _update_locator_json(section: str, key: str, new_selector: str, old_selector: str, extra_fallbacks: list[str] = None):
    with open("app_locators.json", encoding="utf-8") as f:
        locators = json.load(f)

    entry = locators[section][key]
    entry["previous"] = old_selector
    entry["primary"] = new_selector
    entry["healed"] = True

    if extra_fallbacks:
        existing = entry.get("fallback") or []
        if isinstance(existing, str):
            existing = [existing]
        seen = set()
        deduped = [f for f in extra_fallbacks if not (f in seen or seen.add(f))]
        merged = deduped + [f for f in existing if f not in seen and f != new_selector]
        entry["fallback"] = merged
        print(f"[App-Healing] fallback 업데이트 → {merged}")

    with open("app_locators.json", "w", encoding="utf-8") as f:
        json.dump(locators, f, ensure_ascii=False, indent=2)


def try_heal_primary(driver, section: str, key: str, failed_primary: str, fallback_selector: str) -> bool:
    """
    fallback으로 요소를 찾은 뒤 호출됩니다.
    OpenAI에게 XML 기반으로 새 primary selector를 제안받아 업데이트합니다.
    성공 시 True, 실패 시 False 반환.
    """
    full_key = f"{section}.{key}"
    counts = _load_heal_counts()

    if counts.get(full_key, 0) >= MAX_HEAL_COUNT:
        print(f"[App-Healing] {full_key} — healing {MAX_HEAL_COUNT}회 초과. 수동 확인 필요")
        return False

    print(f"[App-Healing] {full_key}: fallback 성공 → OpenAI로 새 primary 탐색")
    element_context = _get_xml_context(driver, fallback_selector)

    with open("app_locators.json", encoding="utf-8") as f:
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
                "content": "You are an Appium test automation expert for Android. Respond only with valid JSON."
            },
            {
                "role": "user",
                "content": (
                    f"기존 primary selector가 변경되었습니다: {failed_primary}\n"
                    f"찾으려는 요소: {section} 섹션의 {key}\n\n"
                    f"아래 Android XML UI 계층에서 [대상 요소]가 바로 찾으려는 요소입니다.\n"
                    f"[대상 요소]의 selector만 제안하세요. 다른 요소의 selector는 절대 포함하지 마세요.\n\n"
                    f"{element_context}\n\n"
                    "위 [대상 요소]에 적합한 Appium selector를 정확히 3개, 아래 순서를 반드시 지켜 제안하세요.\n"
                    "1번째: accessibility_id:<content-desc 값>  (content-desc 속성이 있으면 반드시 이 형식)\n"
                    "2번째: uiautomator:new UiSelector().description(\"<content-desc 값>\")  (content-desc 기반 UiSelector)\n"
                    "3번째: xpath://<class>[@content-desc='<값>'] 또는 [@resource-id='<값>']  (XPath)\n"
                    "content-desc가 없을 때만 id/resource-id 기반으로 대체하세요.\n"
                    "동적으로 변하는 index, bounds 기반 selector는 절대 사용하지 마세요.\n"
                    f"아래 selector는 이미 사용 중이므로 제안하지 마세요:\n{used_selectors}\n\n"
                    '응답 형식: {"selectors": ["accessibility_id:...", "uiautomator:...", "xpath:..."]}'
                )
            }
        ],
        response_format={"type": "json_object"}
    )

    usage = response.usage
    print(
        f"[App-Healing] 토큰 사용량 — "
        f"input: {usage.prompt_tokens}, "
        f"output: {usage.completion_tokens}, "
        f"total: {usage.total_tokens}"
    )

    candidates = json.loads(response.choices[0].message.content).get("selectors", [])

    for i, c in enumerate(candidates, 1):
        print(f"[App-Healing] AI 후보 {i}순위: {c}")

    for i, candidate in enumerate(candidates):
        try:
            by, value = _parse_appium_selector(candidate)
            driver.find_element(by, value)

            extra_fallbacks = [c for c in candidates[i + 1:] if c != candidate]
            _update_locator_json(section, key, candidate, failed_primary, extra_fallbacks)
            counts[full_key] = counts.get(full_key, 0) + 1
            _save_heal_counts(counts)

            print(f"[App-Healing] ✅ {full_key} 새 primary 업데이트: {candidate}")
            print(f"[App-Healing] ⚠️  app_locators.json 업데이트됨 — PR 전 수동 검토 필요")
            return True

        except Exception:
            continue

    counts[full_key] = counts.get(full_key, 0) + 1
    _save_heal_counts(counts)
    print(f"[App-Healing] {full_key} — 새 primary 후보 모두 실패: {candidates}")
    return False

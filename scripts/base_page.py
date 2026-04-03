"""
BasePage — 모든 Page Object의 부모 클래스

탐색 순서:
1. primary selector 시도
2. 실패 시 fallback selector 시도
3. fallback 성공 → OpenAI로 새 primary 제안 → JSON 자동 업데이트 (healed: true)
4. fallback도 없거나 실패 → Exception
"""

import json
import os


class BasePage:
    def __init__(self, page):
        self.page = page
        with open("locators.json", encoding="utf-8") as f:
            self.locators = json.load(f)

    # ── Locator 탐색 ────────────────────────────────────────────────────────

    def _reload_locators(self):
        with open("locators.json", encoding="utf-8") as f:
            self.locators = json.load(f)
        print("[Locator] locators.json 리로드 완료")

    def _build_locator(self, selector: str, value: str = None):
        if value:
            selector = selector.replace("{value}", value)
        return self.page.locator(selector)

    def get_locator(self, section: str, key: str, value: str = None):
        """
        1. primary 시도
        2. 실패 시 fallback 시도 → 성공하면 self-healing으로 primary 복구
        3. 모두 실패 시 Exception
        """
        entry = self.locators[section][key]
        primary = entry["primary"]
        fallback = entry.get("fallback")

        # 1. primary 시도
        try:
            locator = self._build_locator(primary, value)
            locator.wait_for(timeout=5000)
            print(f"[Locator] {section}.{key}: primary 성공 → '{primary}'")
            return locator
        except Exception as e:
            print(f"[Locator] {section}.{key}: primary 실패 → '{primary}' / {e}")

        # 2. fallback 시도 (문자열 또는 배열 모두 지원)
        fallbacks = [fallback] if isinstance(fallback, str) else (fallback or [])
        for fb in fallbacks:
            try:
                locator = self._build_locator(fb, value)
                locator.wait_for(timeout=3000)
                print(f"[Locator] {section}.{key}: fallback 성공 → '{fb}'")
            except Exception as e:
                print(f"[Locator] {section}.{key}: fallback 실패 → '{fb}' / {e}")
                continue

            # 3. OPENAI_API_KEY 있으면 새 primary 제안 요청 (locator 탐색과 분리)
            if os.getenv("OPENAI_API_KEY"):
                try:
                    from self_healing import try_heal_primary
                    healed = try_heal_primary(self.page, section, key, primary, fb)
                    if healed:
                        self._reload_locators()
                except Exception as heal_e:
                    print(f"[Locator] {section}.{key}: self-healing 실패 / {heal_e}")

            return locator

        if not fallbacks:
            print(f"[Locator] {section}.{key}: fallback 없음")

        # 4. 모두 실패 → Exception
        raise Exception(f"[{section}.{key}] primary, fallback 모두 실패")

    # ── 공통 액션 ────────────────────────────────────────────────────────────

    def click(self, section: str, key: str, value: str = None):
        self.get_locator(section, key, value).click()
        self.page.wait_for_load_state("networkidle")

    def fill(self, section: str, key: str, text: str):
        self.get_locator(section, key).fill(text)

    def get_text(self, section: str, key: str, value: str = None) -> str:
        return self.get_locator(section, key, value).text_content()

    def is_visible(self, section: str, key: str, value: str = None) -> bool:
        selector = self.locators[section][key]["primary"]
        if value:
            selector = selector.replace("{value}", value)
        return self.page.locator(selector).is_visible()

    def click_by_text(self, text: str):
        self.click("common", "by_text", value=text)

    def click_by_role_button(self, name: str):
        self.click("common", "by_role_button", value=name)

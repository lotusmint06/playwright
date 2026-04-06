"""
BaseAppPage — 모든 App Page Object의 부모 클래스 (Appium)

탐색 순서:
1. primary selector 시도
2. 실패 시 fallback selector 시도
3. 모두 실패 → Exception

selector 형식:
  accessibility_id:<value>   → content-desc 기반
  xpath:<expression>         → XPath
  id:<resource-id>           → resource-id 기반
"""

import json
import os
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException


class BaseAppPage:
    def __init__(self, driver):
        self.driver = driver
        with open("app_locators.json", encoding="utf-8") as f:
            self.locators = json.load(f)

    def _reload_locators(self):
        with open("app_locators.json", encoding="utf-8") as f:
            self.locators = json.load(f)
        print("[Locator] app_locators.json 리로드 완료")

    # ── Locator 파싱 ─────────────────────────────────────────────────────────

    def _parse_selector(self, selector: str):
        if selector.startswith("accessibility_id:"):
            return AppiumBy.ACCESSIBILITY_ID, selector[len("accessibility_id:"):]
        elif selector.startswith("xpath:"):
            return AppiumBy.XPATH, selector[len("xpath:"):]
        elif selector.startswith("id:"):
            return AppiumBy.ID, selector[len("id:"):]
        elif selector.startswith("uiautomator:"):
            return AppiumBy.ANDROID_UIAUTOMATOR, selector[len("uiautomator:"):]
        return AppiumBy.XPATH, selector

    # ── 요소 탐색 ─────────────────────────────────────────────────────────────

    def get_element(self, section: str, key: str, timeout: int = 15):
        """
        1. primary 시도 (timeout 초 대기)
        2. 실패 시 fallback 시도 (timeout // 2 초 대기)
        3. 모두 실패 → Exception
        """
        entry = self.locators[section][key]
        primary = entry["primary"]
        fallback = entry.get("fallback")

        try:
            by, value = self._parse_selector(primary)
            el = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            print(f"[Locator] {section}.{key}: primary 성공 → '{primary}'")
            return el
        except Exception as e:
            print(f"[Locator] {section}.{key}: primary 실패 → '{primary}' / {e}")

        fallbacks = [fallback] if isinstance(fallback, str) else (fallback or [])
        for fb in fallbacks:
            try:
                by, value = self._parse_selector(fb)
                el = WebDriverWait(self.driver, timeout // 2).until(
                    EC.presence_of_element_located((by, value))
                )
                print(f"[Locator] {section}.{key}: fallback 성공 → '{fb}'")
            except Exception as e:
                print(f"[Locator] {section}.{key}: fallback 실패 → '{fb}' / {e}")
                continue

            # OPENAI_API_KEY 없으면 healing 건너뜀
            if not os.getenv("OPENAI_API_KEY"):
                print(f"[Locator] {section}.{key}: OPENAI_API_KEY 없음 → app-healing 건너뜀")
            if os.getenv("OPENAI_API_KEY"):
                try:
                    from app_self_healing import try_heal_primary
                    healed = try_heal_primary(self.driver, section, key, primary, fb)
                    if healed:
                        self._reload_locators()
                except Exception as heal_e:
                    print(f"[Locator] {section}.{key}: app-healing 실패 / {heal_e}")

            return el

        raise Exception(f"[{section}.{key}] primary, fallback 모두 실패")

    # ── 공통 액션 ─────────────────────────────────────────────────────────────

    def tap(self, section: str, key: str):
        for attempt in range(3):
            try:
                self.get_element(section, key).click()
                return
            except StaleElementReferenceException:
                if attempt == 2:
                    raise
                print(f"[Locator] {section}.{key}: StaleElement, 재탐색 ({attempt + 1}/3)")

    def get_text(self, section: str, key: str) -> str:
        return self.get_element(section, key).text

    def is_displayed(self, section: str, key: str) -> bool:
        try:
            return self.get_element(section, key).is_displayed()
        except Exception:
            return False

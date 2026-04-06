import json
import pytest
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy


def _load_app_config(env: str, app_os: str) -> dict:
    with open("env.json", encoding="utf-8") as f:
        config = json.load(f)
    return config.get(env, {}).get(app_os, {})


@pytest.fixture(scope="function")
def app_driver(pytestconfig):
    """
    Appium driver fixture — function scope

    실행 예시:
        pytest tests_app/ --app-os=android
        pytest tests_app/ --app-os=ios --env=prod
    """
    from appium import webdriver

    app_os = pytestconfig.getoption("--app-os")
    env    = pytestconfig.getoption("--env")
    cfg    = _load_app_config(env, app_os)

    if app_os == "android":
        from appium.options.android import UiAutomator2Options
        options = UiAutomator2Options()
        options.platform_name          = "Android"
        options.device_name            = cfg.get("device_name", "emulator-5554")
        options.platform_version       = cfg.get("platform_version", "")
        options.app_package            = cfg.get("app_package", "") or None
        options.app_activity           = cfg.get("app_activity", "") or None
        options.app                    = cfg.get("app_path", "") or None
        options.no_reset               = True
        options.auto_grant_permissions = True

    else:  # ios
        from appium.options.ios import XCUITestOptions
        options = XCUITestOptions()
        options.platform_name    = "iOS"
        options.device_name      = cfg.get("device_name", "iPhone 15")
        options.platform_version = cfg.get("ios_version", "17.0")
        options.app              = cfg.get("app_path", "") or None
        options.no_reset         = True
        options.automation_name  = "XCUITest"

    driver = webdriver.Remote("http://localhost:4723", options=options)
    driver.implicitly_wait(0)  # 명시적 wait 사용, implicit wait 비활성화

    app_package = cfg.get("app_package", "")
    if app_package:
        state = driver.query_app_state(app_package)
        # 2: background(suspended), 3: background, 4: foreground
        if state >= 2:
            driver.terminate_app(app_package)
        driver.activate_app(app_package)

        # 스플래시 이미지가 사라질 때까지 대기 (app_locators.json > splash.splash_image)
        with open("app_locators.json", encoding="utf-8") as f:
            app_locators = json.load(f)
        splash_selector = app_locators["splash"]["splash_image"]["primary"]
        _, splash_value = splash_selector.split(":", 1)
        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located(
                (AppiumBy.ACCESSIBILITY_ID, splash_value)
            )
        )

    yield driver

    driver.quit()

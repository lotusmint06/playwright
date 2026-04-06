import json
import os
import pytest


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
        options.platform_name         = "Android"
        options.device_name           = cfg.get("device_name", "emulator-5554")
        options.app_package           = cfg.get("app_package", "")
        options.app_activity          = cfg.get("app_activity", "")
        options.app                   = cfg.get("app_path", "") or None
        options.no_reset              = True
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

    yield driver

    driver.quit()

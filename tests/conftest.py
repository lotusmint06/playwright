import json
import os
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def env_config(pytestconfig):
    env      = pytestconfig.getoption("--env")
    platform = pytestconfig.getoption("--platform")
    headless = pytestconfig.getoption("--headless") == "true"
    with open("env.json", encoding="utf-8") as f:
        config = json.load(f)
    cfg = config[env][platform]
    cfg["env"]      = env
    cfg["headless"] = headless
    return cfg


@pytest.fixture(scope="function")
def page(env_config):
    """function scope — xdist 병렬 실행 시 worker 간 충돌 방지"""
    with sync_playwright() as p:
        if env_config.get("platform") == "mo":
            device  = p.devices["iPhone 13"]
            browser = p.chromium.launch(headless=env_config["headless"])
            context = browser.new_context(**device)
        else:
            browser = p.chromium.launch(headless=env_config["headless"])
            context = browser.new_context(viewport={"width": 1920, "height": 1080})

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.goto(env_config["base_url"])

        yield page

        trace_dir = "reports/traces"
        os.makedirs(trace_dir, exist_ok=True)
        context.tracing.stop(path=f"{trace_dir}/trace.zip")
        browser.close()


@pytest.fixture(scope="session")
def session_page(env_config):
    """session scope — 로그인 상태를 유지해야 하는 테스트에서 선택적으로 사용"""
    with sync_playwright() as p:
        if env_config.get("platform") == "mo":
            device  = p.devices["iPhone 13"]
            browser = p.chromium.launch(headless=env_config["headless"])
            context = browser.new_context(**device)
        else:
            browser = p.chromium.launch(headless=env_config["headless"])
            context = browser.new_context(viewport={"width": 1920, "height": 1080})

        page = context.new_page()
        page.goto(env_config["base_url"])

        yield page

        browser.close()

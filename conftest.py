import json
import os
import pytest
import requests
from playwright.sync_api import sync_playwright


TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")


def pytest_addoption(parser):
    parser.addoption("--env", default="qa", choices=["qa", "prod"], help="테스트 환경 (qa/prod)")
    parser.addoption("--platform", default="pc", choices=["pc", "mo"], help="플랫폼 (pc/mo)")
    parser.addoption("--headless", default="false", choices=["true", "false"], help="헤드리스 모드 (true/false)")


def pytest_configure(config):  # noqa: ARG001
    """테스트 시작 전 locators.json 정합성 자동 검증 + heal count 리셋"""
    import subprocess
    result = subprocess.run(["python3", "validate_locators.py"], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.exit(f"Locator 검증 실패:\n{result.stdout}\n{result.stderr}")

    if os.path.exists(".heal_count.json"):
        os.remove(".heal_count.json")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def env_config(pytestconfig):
    env = pytestconfig.getoption("--env")
    platform = pytestconfig.getoption("--platform")
    headless = pytestconfig.getoption("--headless") == "true"
    with open("env.json", encoding="utf-8") as f:
        config = json.load(f)
    cfg = config[env][platform]
    cfg["env"] = env
    cfg["headless"] = headless
    return cfg


@pytest.fixture(scope="function")
def page(env_config):
    """function scope — xdist 병렬 실행 시 worker 간 충돌 방지"""
    with sync_playwright() as p:
        if env_config["platform"] == "mo":
            device = p.devices["iPhone 13"]
            browser = p.chromium.launch(headless=env_config["headless"])
            context = browser.new_context(**device)
        else:
            browser = p.chromium.launch(headless=env_config["headless"])
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.goto(env_config["base_url"])

        yield page

        # 실패 시 trace 저장
        trace_dir = "reports/traces"
        os.makedirs(trace_dir, exist_ok=True)
        context.tracing.stop(path=f"{trace_dir}/trace.zip")
        browser.close()


@pytest.fixture(scope="session")
def session_page(env_config):
    """session scope — 로그인 상태를 유지해야 하는 테스트에서 선택적으로 사용"""
    with sync_playwright() as p:
        if env_config["platform"] == "mo":
            device = p.devices["iPhone 13"]
            browser = p.chromium.launch(headless=env_config["headless"])
            context = browser.new_context(**device)
        else:
            browser = p.chromium.launch(headless=env_config["headless"])
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )

        page = context.new_page()
        page.goto(env_config["base_url"])

        yield page

        browser.close()


# ── Hooks ─────────────────────────────────────────────────────────────────────

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):  # noqa: ARG001
    """실패 시 스크린샷 저장"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page:
            screenshot_dir = "reports/screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            page.screenshot(path=f"{screenshot_dir}/{item.name}.png")


def pytest_terminal_summary(terminalreporter, exitstatus):  # noqa: ARG001
    """테스트 완료 후 Teams webhook 전송"""
    if not TEAMS_WEBHOOK_URL:
        return

    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    error = len(terminalreporter.stats.get("error", []))
    total = passed + failed + error

    status_icon = "✅" if failed == 0 and error == 0 else "❌"

    payload = {
        "text": (
            f"{status_icon} **테스트 완료**\n"
            f"- 전체: {total}건\n"
            f"- 통과: {passed}건\n"
            f"- 실패: {failed}건\n"
            f"- 오류: {error}건"
        )
    }

    try:
        requests.post(TEAMS_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Teams webhook 전송 실패: {e}")

import os
import pytest
import requests


TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")


def pytest_addoption(parser):
    parser.addoption("--env",      default="qa",      choices=["qa", "prod"],         help="테스트 환경 (qa/prod)")
    parser.addoption("--platform", default="pc",       choices=["pc", "mo"],           help="웹 플랫폼 (pc/mo)")
    parser.addoption("--headless", default="false",    choices=["true", "false"],      help="헤드리스 모드 (true/false)")
    parser.addoption("--app-os",   default="android",  choices=["android", "ios"],     help="앱 OS (android/ios)")


def pytest_configure(config):
    """테스트 시작 전 locators.json 정합성 검증 + heal count 리셋"""
    import subprocess
    result = subprocess.run(["python3", "validate_locators.py"], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.exit(f"Locator 검증 실패:\n{result.stdout}\n{result.stderr}")

    for heal_file in (".heal_count.json", ".app_heal_count.json"):
        if os.path.exists(heal_file):
            os.remove(heal_file)


# ── Hooks ─────────────────────────────────────────────────────────────────────

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):  # noqa: ARG001
    """실패 시 스크린샷 저장 — 웹(page)과 앱(app_driver) 공통 처리"""
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return

    screenshot_dir = "reports/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    path = f"{screenshot_dir}/{item.name}.png"

    page = item.funcargs.get("page")
    if page:
        page.screenshot(path=path)
        return

    app_driver = item.funcargs.get("app_driver")
    if app_driver:
        app_driver.save_screenshot(path)


def pytest_terminal_summary(terminalreporter, exitstatus):  # noqa: ARG001
    """테스트 완료 후 Teams webhook 전송"""
    if not TEAMS_WEBHOOK_URL:
        return

    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    error  = len(terminalreporter.stats.get("error",  []))
    total  = passed + failed + error

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

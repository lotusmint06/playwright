"""
Appium 디바이스 연결 및 앱 실행 확인 테스트

실행:
    pytest tests_app/test_connection.py --app-os=android -v -s
"""


def test_device_connected(app_driver):
    """Appium 서버 ↔ 디바이스 연결 확인"""
    assert app_driver.session_id is not None, "Appium 세션이 생성되지 않았습니다."


def test_device_info(app_driver):
    """연결된 디바이스 기본 정보 출력"""
    caps = app_driver.capabilities

    platform    = caps.get("platformName", "")
    version     = caps.get("platformVersion", "")
    device_name = caps.get("deviceName", "") or caps.get("deviceUDID", "")

    print(f"\n[Device] {device_name} | Android {version}")

    assert platform.lower() == "android", f"예상: android, 실제: {platform}"
    assert version != "", "platformVersion이 비어 있습니다."


def test_screen_size(app_driver):
    """화면 크기 조회"""
    size = app_driver.get_window_size()

    width  = size.get("width", 0)
    height = size.get("height", 0)

    print(f"\n[Screen] {width} x {height}")

    assert width  > 0, "화면 너비를 가져올 수 없습니다."
    assert height > 0, "화면 높이를 가져올 수 없습니다."


def test_app_launched(app_driver):
    """앱 실행 확인 — 현재 포그라운드 패키지가 배달의민족인지 검증"""
    current_package = app_driver.current_package
    print(f"\n[App] 현재 실행 중인 패키지: {current_package}")
    assert current_package == "com.sampleapp", (
        f"앱이 실행되지 않았습니다. 현재 패키지: {current_package}"
    )

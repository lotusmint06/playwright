"""
앱 메인화면 테스트

실행:
    pytest tests_app/test_main.py --app-os=android -v -s
"""

from scripts_app.main_page import MainPage


def test_tap_pizza(app_driver):
    """메인화면에서 피자 카테고리 탭 후 뒤로가기"""
    page = MainPage(app_driver)
    page.tap_pizza()
    page.tap_back()

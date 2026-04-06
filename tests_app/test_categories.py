"""
앱 메인화면 카테고리 API 기반 탭 테스트

실행:
    pytest tests_app/test_categories.py --app-os=android -v -s
"""

from tools.api_client import get_food_categories
from scripts_app.main_page import MainPage
from scripts_app.food_list_page import FoodListPage


def test_tap_all_api_categories(app_driver):
    """API에서 받은 카테고리 목록을 순서대로 탭 → 필터 칩 노출 확인 → 뒤로가기 반복"""
    main = MainPage(app_driver)
    food_list = FoodListPage(app_driver)
    categories = get_food_categories()

    for cat in categories:
        name = cat["content_desc"]
        main.tap_category(name)
        if not cat["is_webview"]:
            assert food_list.is_filter_chip_displayed(name), f"[{name}] 필터 칩 미노출"
        main.tap_back(webview=cat["is_webview"])

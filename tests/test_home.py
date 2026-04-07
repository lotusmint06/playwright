import pytest
from scripts.home_page import HomePage


@pytest.fixture
def home_page(page):
    return HomePage(page)


def test_click_login_navigates_to_login(home_page):
    """메인화면 로그인 버튼 클릭 시 로그인 페이지로 이동"""
    home_page.click_login_btn()
    assert "accounts.hanatour.com" in home_page.get_current_url()

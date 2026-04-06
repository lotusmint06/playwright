import os
import pytest
from scripts.login_page import LoginPage

TEST_EMAIL = os.getenv("TEST_EMAIL", "")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "")


@pytest.fixture
def login_page(page, env_config):
    lp = LoginPage(page)
    lp.base_url = env_config["base_url"]
    return lp


def test_login_page_loaded(login_page):
    """로그인 페이지 정상 로딩 확인"""
    assert login_page.get_title() == "하나투어 : 꿈꾸는 대로, 펼쳐지다"
    assert login_page.is_submit_btn_visible()


def test_login_fail_empty_fields(login_page):
    """아이디/비밀번호 미입력 시 로그인 버튼 동작 확인"""
    login_page.click("login", "submit_btn")
    assert login_page.get_current_url() == login_page.base_url + "/"


def test_login_fail_wrong_credentials(login_page):
    """잘못된 계정 정보로 로그인 시도 시 에러 팝업 확인"""
    login_page.login("wrong@hanatour.com", "wrongpassword")
    assert login_page.is_error_popup_visible()
    login_page.click("login", "error_popup_confirm")


def test_find_id_button(login_page):
    """아이디 찾기 버튼 클릭"""
    login_page.click_and_navigate("login", "find_id_btn")
    assert login_page.get_current_url() != login_page.base_url + "/"


def test_find_password_button(login_page):
    """비밀번호 찾기 버튼 클릭"""
    login_page.click_and_navigate("login", "find_password_btn")
    assert login_page.get_current_url() != login_page.base_url + "/"


def test_signup_button(login_page):
    """통합 회원 가입하기 버튼 클릭"""
    login_page.click_and_navigate("login", "signup_btn")
    assert login_page.get_current_url() != login_page.base_url + "/"


def test_non_member_button(login_page):
    """비회원 예약조회 버튼 클릭"""
    login_page.click_and_navigate("login", "non_member_btn")
    assert login_page.get_current_url() != login_page.base_url + "/"


@pytest.mark.skipif(not TEST_EMAIL or not TEST_PASSWORD, reason="TEST_EMAIL / TEST_PASSWORD 환경변수 필요")
def test_login_success(login_page):
    """정상 계정으로 로그인 성공"""
    login_page.login(TEST_EMAIL, TEST_PASSWORD)
    assert login_page.get_current_url() != login_page.base_url + "/"
    assert not login_page.is_submit_btn_visible()

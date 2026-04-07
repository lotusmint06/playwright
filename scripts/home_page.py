from scripts.base_page import BasePage


class HomePage(BasePage):
    def click_login_btn(self):
        self.click_and_navigate("home", "login_button")

    def get_current_url(self) -> str:
        return self.page.url

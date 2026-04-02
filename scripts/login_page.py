from scripts.base_page import BasePage


class LoginPage(BasePage):
    def login(self, email: str, password: str):
        self.click("login", "email_input")
        self.fill("login", "email_input", email)
        self.click("login", "password_input")
        self.fill("login", "password_input", password)
        self.click("login", "submit_btn")

    def get_title(self) -> str:
        return self.page.title()

    def get_current_url(self) -> str:
        return self.page.url

    def is_submit_btn_visible(self) -> bool:
        return self.get_locator("login", "submit_btn").is_visible()

    def is_error_popup_visible(self) -> bool:
        return self.get_locator("login", "error_popup").is_visible()

    def get_error_message(self) -> str:
        return self.get_text("login", "error_popup")

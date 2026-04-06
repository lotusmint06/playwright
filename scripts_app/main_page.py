from scripts_app.base_app_page import BaseAppPage


class MainPage(BaseAppPage):
    def tap_pizza(self):
        self.tap("main", "pizza_btn")

    def tap_back(self):
        self.tap("main", "back_btn")

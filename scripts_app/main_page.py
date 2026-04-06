from scripts_app.base_app_page import BaseAppPage


class MainPage(BaseAppPage):
    def tap_category(self, name: str):
        """category_btn {value} 템플릿 사용 — healing 미지원, fallback 없음"""
        self.tap("main", "category_btn", value=name)

    def tap_jokbal(self):
        self.tap("main", "jokbal_btn")

    def tap_donkkaseu(self):
        self.tap("main", "donkkaseu_btn")

    def tap_pizza(self):
        self.tap("main", "pizza_btn")

    def tap_jjim(self):
        self.tap("main", "jjim_btn")

    def tap_back(self, webview: bool = False):
        if webview:
            self.tap("main", "webview_back_btn")
        else:
            self.tap("main", "back_btn")

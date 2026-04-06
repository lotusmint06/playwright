from scripts_app.base_app_page import BaseAppPage


class FoodListPage(BaseAppPage):
    def is_filter_chip_displayed(self, name: str) -> bool:
        """카테고리 필터 칩이 노출되는지 확인 (selected 속성 미지원 → 노출 여부로 대체)"""
        return self.is_displayed("food_list", "filter_chip", value=name)

"""
배민 가게 목록 API 클라이언트

카테고리별 가게 목록을 조회한다.

    python scripts_api/shop_api.py

환경변수 설정 (.env):
    BAEMIN_COOKIE : __cf_bm 등 쿠키값
    (공통 환경변수는 scripts_api/base_api.py 참고)
"""

from curl_cffi import requests
from scripts_api.base_api import COMMON_HEADERS, COMMON_PARAMS

_BASE_URL = "https://shopdp-api.baemin.com/v4/FOOD_CATEGORY/shops"


class SortOption:
    DEFAULT  = "SORT__DEFAULT"   # 기본순
    ORDER    = "SORT__ORDER"     # 주문 많은 순
    FAVORITE = "SORT__FAVORITE"  # 찜 많은 순
    DISTANCE = "SORT__DISTANCE"  # 가까운 순
    STAR     = "SORT__STAR"      # 별점 높은 순


def get_shops(display_category: str, sort: str = SortOption.DEFAULT, offset: int = 0, limit: int = 30) -> list[dict]:
    """
    카테고리별 가게 목록을 반환한다.

    Args:
        display_category: 카테고리 코드 (예: "FOOD_CATEGORY_JOKBAL")
        offset: 페이지 오프셋
        limit: 조회 개수 (최대 30)

    반환 예시:
        [
            {"shopNo": 12345, "shopName": "족발집", "rating": 4.8, ...},
            ...
        ]
    """
    params = {
        **COMMON_PARAMS,
        "displayCategory": display_category,
        "filter": "",
        "sort": sort,
        "offset": offset,
        "limit": limit,
    }
    headers = {
        **COMMON_HEADERS,
        "Host": "shopdp-api.baemin.com",
    }

    res = requests.get(_BASE_URL, headers=headers, params=params, impersonate="chrome")
    res.raise_for_status()
    data = res.json()

    return data.get("data", {}).get("shops", [])


if __name__ == "__main__":
    shops = get_shops("FOOD_CATEGORY_JOKBAL", SortOption.FAVORITE)
    print(f"가게 수: {len(shops)}")
    for shop in shops[:30]:
        info    = shop.get("shopInfo", {})
        stats   = shop.get("shopStatistics", {})
        ad_type = shop.get("logInfo", {}).get("performanceAdTrackingLog", {}).get("performanceAdType", "")
        ad_tag  = " [광고]" if ad_type == "CPC" else ""
        print(f"  {info.get('shopName')}{ad_tag} — 평점 {stats.get('averageStarScore', '-')}")

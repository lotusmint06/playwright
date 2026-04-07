"""
배민 가게 상세 API 클라이언트

목록 API 응답의 가게 데이터를 받아 상세 정보를 조회한다.

    python scripts_api/shop_detail_api.py

환경변수 설정 (.env):
    BAEMIN_COOKIE : __cf_bm 등 쿠키값
    (공통 환경변수는 scripts_api/base_api.py 참고)
"""

from curl_cffi import requests
from scripts_api.base_api import COMMON_HEADERS, COMMON_PARAMS
from scripts_api.shop_api import SortOption

_BASE_URL = "https://shop-detail-api.baemin.com/api/v2/shops/{shop_number}/detail"


def get_shop_detail(shop: dict, sort: str = SortOption.DEFAULT) -> dict:
    """
    목록 API 응답의 가게 dict를 받아 상세 정보를 반환한다.

    Args:
        shop: get_shops() 응답의 가게 dict
        sort: 목록 요청 시 사용한 정렬 기준 (context 유지용)

    반환:
        상세 API 응답 data dict
    """
    shop_number      = shop["shopInfo"]["shopNumber"]
    campaign_id      = shop.get("adInfo", {}).get("campaignId", "")
    bypass_data      = shop.get("contextInfo", {}).get("bypassData", "")
    delivery_type    = shop.get("contextInfo", {}).get("exposedDeliveryType", "COMMON")
    first_menu_id    = (shop.get("shopInfo", {}).get("menus") or [{}])[0].get("menuId", "")

    params = {
        **COMMON_PARAMS,
        "bypassData": bypass_data,
        "campaignId": campaign_id,
        "displayGroup": "FOOD_CATEGORY",
        "emphasizeMenuGroup[menuClick][menuIds]": first_menu_id,
        "exposedDeliveryType": delivery_type,
        "filter": "",
        "lat": COMMON_PARAMS["latitude"],
        "lat4Distance": COMMON_PARAMS["latitude"],
        "lng": COMMON_PARAMS["longitude"],
        "lng4Distance": COMMON_PARAMS["longitude"],
        "mem": "000000000000",
        "sort": sort,
    }
    # 상세 API는 lat/lng 키 사용 (목록은 latitude/longitude)
    params.pop("latitude", None)
    params.pop("longitude", None)
    params.pop("memberNumber", None)

    headers = {
        **COMMON_HEADERS,
        "Host": "shop-detail-api.baemin.com",
        "Authorization": "Bearer guest",
    }

    url = _BASE_URL.format(shop_number=shop_number)
    res = requests.get(url, headers=headers, params=params, impersonate="chrome")
    res.raise_for_status()
    return res.json().get("data", {})


if __name__ == "__main__":
    from scripts_api.shop_api import get_shops, SortOption

    shops = get_shops("FOOD_CATEGORY_JOKBAL", SortOption.FAVORITE)
    first = shops[0]
    print(f"대상 가게: {first['shopInfo']['shopName']}")

    detail = get_shop_detail(first, sort=SortOption.FAVORITE)
    print(f"상세 응답 키: {list(detail.keys())}")

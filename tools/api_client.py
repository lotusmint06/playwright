"""
배민 Gateway API 클라이언트

테스트에서 API 응답 값을 locator value 또는 assert 인자로 활용하기 위한 도구.
직접 실행 시 카테고리 목록을 출력한다.

    python tools/api_client.py

환경변수 설정 (.env 또는 export):
    BAEMIN_USER_BAEDAL   : User-Baedal 헤더값
    BAEMIN_DVC_UNIQ_ID   : 디바이스 고유 ID (dvc_uniq_id, idfv)
    BAEMIN_DVCID         : 디바이스 ID (dvcid)
    BAEMIN_ADJUST_ID     : Adjust 트래킹 ID
    BAEMIN_PERSEUS_CLIENT_ID : Perseus 클라이언트 ID
    BAEMIN_PERSEUS_SESSION_ID: Perseus 세션 ID
    BAEMIN_SESSION_ID    : 세션 ID
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


_BASE_URL = "https://gateway-api.baemin.com/v3/gateway/elements"

_HEADERS = {
    "Host": "gateway-api.baemin.com",
    "Accept": "*/*",
    "Accept-Language": "ko",
    "User-Baedal": os.getenv("BAEMIN_USER_BAEDAL", ""),
    "Carrier": "6553565535",
    "User-Agent": "iph1_16.0.1",
    "Authorization": "Bearer guest",
}

_PARAMS = {
    "actionTrackingKey": "Organic",
    "adid": "00000000-0000-0000-0000-000000000000",
    "adjustId": os.getenv("BAEMIN_ADJUST_ID", ""),
    "appver": "16.0.1",
    "carrier": "6553565535",
    "deviceModel": "iPhone17,2",
    "dongCode": "11530112",
    "dvc_uniq_id": os.getenv("BAEMIN_DVC_UNIQ_ID", ""),
    "dvcid": os.getenv("BAEMIN_DVCID", ""),
    "idfv": os.getenv("BAEMIN_DVC_UNIQ_ID", ""),
    "lat": "37.48198901",
    "lng": "126.82225986",
    "memberNo": "000000000000",
    "oscd": "1",
    "osver": "18.1",
    "perseusClientId": os.getenv("BAEMIN_PERSEUS_CLIENT_ID", ""),
    "perseusSessionId": os.getenv("BAEMIN_PERSEUS_SESSION_ID", ""),
    "sessionid": os.getenv("BAEMIN_SESSION_ID", ""),
    "site": "7jWXRELC2e",
    "zipCode": "08362",
}


def _build_content_desc(icon: dict) -> str:
    """badge.badgeText + name 조합으로 앱 content-desc 생성."""
    badge = icon.get("badge") or {}
    badge_text = badge.get("badgeText", "") if badge.get("badgeType") == "TEXT" else ""
    return f"{badge_text}{icon['name']}"


def get_food_categories() -> list[dict]:
    """
    음식배달 탭의 카테고리 목록을 반환한다.

    반환 예시:
        [
            {"content_desc": "최대6천원배짱할인", "is_webview": True},
            {"content_desc": "족발·보쌈",        "is_webview": False},
            ...
        ]
    """
    res = requests.get(_BASE_URL, headers=_HEADERS, params=_PARAMS)
    res.raise_for_status()
    data = res.json()

    _EXCLUDE = {"한그릇", "바로 픽업"}

    service_tabs = data["data"]["tabContents"]["serviceTabs"]
    food_tab = next(tab for tab in service_tabs if tab["serviceType"] == "FOOD")
    return [
        {
            "content_desc": _build_content_desc(icon),
            "is_webview": "webview" in (icon.get("deepLink") or ""),
        }
        for icon in food_tab["icons"]
        if icon["name"] not in _EXCLUDE
    ]


if __name__ == "__main__":
    categories = get_food_categories()
    print("카테고리 목록:")
    for cat in categories:
        tag = "[웹뷰]" if cat["is_webview"] else "[네이티브]"
        print(f"  {tag} {cat['content_desc']}")

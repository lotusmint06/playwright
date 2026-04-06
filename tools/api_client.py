"""
배민 Gateway API 클라이언트

테스트에서 API 응답 값을 locator value 또는 assert 인자로 활용하기 위한 도구.
직접 실행 시 카테고리 목록을 출력한다.

    python tools/api_client.py
"""

import requests


_BASE_URL = "https://gateway-api.baemin.com/v3/gateway/elements"

_HEADERS = {
    "Host": "gateway-api.baemin.com",
    "Accept": "*/*",
    "Accept-Language": "ko",
    "User-Baedal": "xyzcdL4qorK8KB9W6BnEyh4GqbB8XH5vXNVbbhAOLi+c5s9eOVef6nWDKGgDw8rwyN73jaNbZVKdBtsOU2EP82O+IhcsXmhC7MtGx5ANfmGJAK49O9DCmnQaBudtXOsATLWLxkO044WX79KVPKR0mfd/Z3fWWwiO+XIOnuqgGnvMLAUUKG3lB3wbCz5lHeNJBvgjo4d+39lALoeBC9VaCw==",
    "Carrier": "6553565535",
    "User-Agent": "iph1_16.0.1",
    "Authorization": "Bearer guest",
}

_PARAMS = {
    "actionTrackingKey": "Organic",
    "adid": "00000000-0000-0000-0000-000000000000",
    "adjustId": "81cde4547f67a7e7fbd2905205dcb343",
    "appver": "16.0.1",
    "carrier": "6553565535",
    "deviceModel": "iPhone17,2",
    "dongCode": "11530112",
    "dvc_uniq_id": "4AF4F9AD-10E7-41C8-9E59-247EE62540D0",
    "dvcid": "OPUD85EAE52B-D7C5-47CE-B2B7-2AF3C8A6D6E7",
    "idfv": "4AF4F9AD-10E7-41C8-9E59-247EE62540D0",
    "lat": "37.48198901",
    "lng": "126.82225986",
    "memberNo": "000000000000",
    "oscd": "1",
    "osver": "18.1",
    "perseusClientId": "1775480710022.0293758061.cpbekadglt",
    "perseusSessionId": "1775480710023.1465161733.oxockigsxt",
    "sessionid": "f3f83ba609823404d10e8a574ace1708",
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

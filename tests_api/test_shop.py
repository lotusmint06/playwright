"""
가게 목록 API 테스트

정렬 기준별 응답 검증:
- 별점순: averageStarScore 내림차순
- 거리순: distancePhrase 오름차순
- 광고 포함 여부: 기본순에서 CPC 광고 포함

실행:
    pytest tests_api/test_shop.py -v -s
"""


def _is_ad(shop: dict) -> bool:
    return shop.get("logInfo", {}).get("performanceAdTrackingLog", {}).get("performanceAdType") == "CPC"


def _star_score(shop: dict) -> float:
    return shop.get("shopStatistics", {}).get("averageStarScore", 0.0)


def _distance_km(shop: dict) -> float:
    phrase = shop.get("deliveryInfos", [{}])[0].get("distancePhrase", "0km")
    return float(phrase.replace("km", ""))


# ── 테스트 ────────────────────────────────────────────────────────────────────

def test_shop_list_count(shops_default):
    """기본 요청(offset=0, limit=30) 시 1개 이상 limit 이하 반환 — offset은 페이지네이션 역할 (0→30→60...)"""
    print(f"\n[결과] 가게 수: {len(shops_default)}")
    assert 0 < len(shops_default) <= 30


def test_sort_by_star_descending(shops_star):
    """별점순 정렬 시 광고 제외 가게의 별점이 내림차순"""
    non_ads = [(s.get("shopInfo", {}).get("shopName"), _star_score(s)) for s in shops_star if not _is_ad(s)]
    scores = [score for _, score in non_ads]
    print(f"\n[결과] 별점순 (광고 제외 {len(non_ads)}개):")
    for name, score in non_ads:
        print(f"  {name} — {score}")
    assert scores == sorted(scores, reverse=True), f"별점 내림차순 아님: {scores}"


def test_sort_by_distance_ascending(shops_distance):
    """거리순 정렬 시 광고 제외 가게의 거리가 오름차순"""
    non_ads = [(s.get("shopInfo", {}).get("shopName"), _distance_km(s)) for s in shops_distance if not _is_ad(s)]
    distances = [d for _, d in non_ads]
    print(f"\n[결과] 거리순 (광고 제외 {len(non_ads)}개):")
    for name, dist in non_ads:
        print(f"  {name} — {dist}km")
    assert distances == sorted(distances), f"거리 오름차순 아님: {distances}"


def test_default_sort_contains_ads(shops_default):
    """기본순에서 CPC 광고 가게 현황 확인 (광고는 시간대·예산에 따라 없을 수 있어 assert 없음)"""
    ad_shops = [s.get("shopInfo", {}).get("shopName") for s in shops_default if _is_ad(s)]
    print(f"\n[결과] 광고 가게 ({len(ad_shops)}개): {ad_shops}")

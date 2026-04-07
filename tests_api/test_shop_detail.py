"""
가게 상세 API 테스트

실행 흐름:
  1. tests_api/fixtures/shops_default.json 로드 (test_shop.py 실행 후 생성)
  2. 상위 N개 가게에 대해 상세 API 순차 호출 (1초 딜레이)
  3. 목록↔상세 데이터 정합성 assert
  4. tests_api/fixtures/shop_details.json 저장

실행:
    pytest tests_api/ -v -s          # 전체 (test_shop.py → test_shop_detail.py 순)
    pytest tests_api/test_shop_detail.py -v -s  # 단독 (shops_default.json 필요)
"""

import json
import os
import time
import pytest

from scripts_api.shop_detail_api import get_shop_detail
from scripts_api.shop_api import SortOption

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
DETAIL_SAMPLE_COUNT = 10


def _load(filename: str):
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(filename: str, data: object):
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@pytest.fixture(scope="session")
def shop_details():
    """shops_default.json에서 로드 → 상세 API 순차 호출 → shop_details.json 저장"""
    shops = _load("shops_default.json")
    details = []
    for shop in shops[:DETAIL_SAMPLE_COUNT]:
        name = shop["shopInfo"]["shopName"]
        print(f"\n  → 상세 조회: {name}")
        detail = get_shop_detail(shop, sort=SortOption.DEFAULT)
        details.append({"list": shop, "detail": detail})
        time.sleep(1)
    _save("shop_details.json", details)
    return details


# ── 테스트 ────────────────────────────────────────────────────────────────────

def test_shop_name_matches_list(shop_details):
    """상세 API의 shopName이 목록 API와 일치"""
    for item in shop_details:
        list_name   = item["list"]["shopInfo"]["shopName"]
        detail_name = item["detail"]["shop"]["shopName"]
        print(f"\n[{list_name}] 목록: {list_name} / 상세: {detail_name}")
        assert list_name == detail_name, f"가게명 불일치: 목록={list_name}, 상세={detail_name}"


def test_minimum_order_price_matches_list(shop_details):
    """상세 API의 최소주문금액이 목록 API와 일치"""
    for item in shop_details:
        name         = item["list"]["shopInfo"]["shopName"]
        list_price   = item["list"]["shopInfo"]["minimumOrderPrice"]
        detail_price = item["detail"]["shop"]["shopMinimumOrderPrice"]
        print(f"\n[{name}] 목록: {list_price}원 / 상세: {detail_price}원")
        assert list_price == detail_price, f"최소주문금액 불일치: 목록={list_price}, 상세={detail_price}"


def test_shop_is_possible_to_order(shop_details):
    """상세 API에서 모든 가게가 주문 가능 상태"""
    for item in shop_details:
        name     = item["detail"]["shop"]["shopName"]
        possible = item["detail"]["shop"]["isPossibleToOrder"]
        print(f"\n[{name}] isPossibleToOrder: {possible}")
        assert possible is True, f"{name}: 주문 불가 상태"


def test_review_rating_matches_list(shop_details):
    """상세 API의 별점이 목록 API와 일치"""
    for item in shop_details:
        name         = item["list"]["shopInfo"]["shopName"]
        list_score   = item["list"]["shopStatistics"]["averageStarScore"]
        detail_score = float(item["detail"]["reviewSummary"]["reviewRatingText"])
        print(f"\n[{name}] 목록: {list_score} / 상세: {detail_score}")
        assert list_score == detail_score, f"별점 불일치: 목록={list_score}, 상세={detail_score}"

"""
가게 상세 API 테스트

목록 API → 상세 API 흐름에서 데이터 정합성 검증:
- 가게명 일치
- 최소주문금액 일치
- 주문 가능 여부
- 별점 일치

실행:
    pytest tests_api/test_shop_detail.py -v -s
"""

import pytest


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
        name        = item["list"]["shopInfo"]["shopName"]
        list_price  = item["list"]["shopInfo"]["minimumOrderPrice"]
        detail_price = item["detail"]["shop"]["shopMinimumOrderPrice"]
        print(f"\n[{name}] 목록: {list_price}원 / 상세: {detail_price}원")
        assert list_price == detail_price, f"최소주문금액 불일치: 목록={list_price}, 상세={detail_price}"


def test_shop_is_possible_to_order(shop_details):
    """상세 API에서 모든 가게가 주문 가능 상태"""
    for item in shop_details:
        name = item["detail"]["shop"]["shopName"]
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

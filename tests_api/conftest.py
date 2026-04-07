import json
import os
import time
import pytest

from scripts_api.shop_api import get_shops, SortOption
from scripts_api.shop_detail_api import get_shop_detail

CATEGORY = "FOOD_CATEGORY_JOKBAL"
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
DETAIL_SAMPLE_COUNT = 10


def _save(filename: str, data: object):
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load(filename: str) -> list:
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def shops_default():
    data = get_shops(CATEGORY, SortOption.DEFAULT)
    _save("shops_default.json", data)
    time.sleep(1)
    return data


@pytest.fixture(scope="session")
def shops_star():
    data = get_shops(CATEGORY, SortOption.STAR)
    _save("shops_star.json", data)
    time.sleep(1)
    return data


@pytest.fixture(scope="session")
def shops_distance():
    data = get_shops(CATEGORY, SortOption.DISTANCE)
    _save("shops_distance.json", data)
    time.sleep(1)
    return data


@pytest.fixture(scope="session")
def shops_favorite():
    data = get_shops(CATEGORY, SortOption.FAVORITE)
    _save("shops_favorite.json", data)
    time.sleep(1)
    return data


@pytest.fixture(scope="session")
def shop_details(shops_default):
    """목록 상위 N개의 상세 API 호출 결과 — shops_default fixture에 의존"""
    details = []
    for shop in shops_default[:DETAIL_SAMPLE_COUNT]:
        detail = get_shop_detail(shop, sort=SortOption.DEFAULT)
        details.append({"list": shop, "detail": detail})
        time.sleep(1)
    _save("shop_details.json", details)
    return details

import json
import os
import time
import pytest

from scripts_api.shop_api import get_shops, SortOption

CATEGORY = "FOOD_CATEGORY_JOKBAL"
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _save(filename: str, data: object):
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load(filename: str):
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

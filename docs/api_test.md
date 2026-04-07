# API 테스트 가이드

배민 Shop 목록 및 상세 API를 대상으로 한 자동화 테스트 설계 및 구현 내용을 정리합니다.

---

## 목차

1. [개요](#개요)
2. [프로젝트 구조](#프로젝트-구조)
3. [환경 설정](#환경-설정)
4. [API 클라이언트](#api-클라이언트)
5. [테스트 케이스](#테스트-케이스)
6. [실행 방법](#실행-방법)
7. [예외 사항](#예외-사항)

---

## 개요

배민 Shop API를 호출해 정렬 기준·광고 포함 여부, 목록↔상세 데이터 정합성을 자동화로 검증합니다.

**대상 API**

```
GET https://shopdp-api.baemin.com/v4/FOOD_CATEGORY/shops       # 목록
GET https://shop-detail-api.baemin.com/api/v2/shops/{id}/detail # 상세
```

**특이 사항**

- Cloudflare Bot Management(`__cf_bm` 쿠키)로 보호되어 있어 일반 `requests` 라이브러리는 403 반환
- `curl_cffi`의 Chrome TLS 핑거프린트 impersonation으로 우회

**테스트 실행 흐름**

```
pytest tests_api/
  ├─ test_shop.py
  │    └─ conftest.py fixture (session scope)
  │         ├─ 목록 API 호출 → shops_default.json / shops_star.json / shops_distance.json / shops_favorite.json 저장
  │         ├─ assert: 가게 수 0 < count <= 30
  │         ├─ assert: 별점순 내림차순 (광고 제외)
  │         ├─ assert: 거리순 오름차순 (광고 제외)
  │         └─ print: 광고 가게 현황 출력 (assert 없음 — 시간대별 변동)
  └─ test_shop_detail.py
       └─ shop_details fixture (session scope)
            ├─ shops_default.json 로드
            ├─ 상세 API 순차 호출 (상위 10개, 1초 딜레이) → shop_details.json 저장
            ├─ assert: 가게명 일치
            ├─ assert: 최소주문금액 일치
            ├─ assert: 주문 가능 상태
            └─ assert: 별점 일치
```

테스트 실행 시 API를 직접 호출하고 응답을 `tests_api/fixtures/`에 저장합니다.
저장된 fixture는 다음 실행에서 재사용하지 않으며, 매 실행마다 최신 데이터로 갱신됩니다.

---

## 프로젝트 구조

```
scripts_api/
├── __init__.py
├── base_api.py          # 공통 헤더·파라미터 (COMMON_HEADERS, COMMON_PARAMS)
├── shop_api.py          # 가게 목록 API 클라이언트 (get_shops, SortOption)
└── shop_detail_api.py   # 가게 상세 API 클라이언트 (get_shop_detail)

tests_api/
├── __init__.py
├── conftest.py          # session fixture — 목록 API 호출 + fixture JSON 저장
├── fixtures/            # API 응답 저장 (gitignore, 테스트 실행 시 자동 갱신)
│   ├── shops_default.json   # 기본순 목록 (test_shop.py 실행 후 생성)
│   ├── shops_star.json      # 별점순 목록
│   ├── shops_distance.json  # 거리순 목록
│   ├── shops_favorite.json  # 찜순 목록
│   └── shop_details.json    # 상세 응답 (test_shop_detail.py 실행 후 생성)
├── test_shop.py         # 가게 목록 API 테스트
└── test_shop_detail.py  # 가게 상세 API 테스트 (목록↔상세 교차 검증)
```

---

## 환경 설정

`.env` 파일에 아래 항목을 설정합니다. (`.env.example` 참고)


| 환경변수                        |
| --------------------------- |
| `BAEMIN_USER_BAEDAL`        |
| `BAEMIN_DVC_UNIQ_ID`        |
| `BAEMIN_DVCID`              |
| `BAEMIN_ADJUST_ID`          |
| `BAEMIN_PERSEUS_CLIENT_ID`  |
| `BAEMIN_PERSEUS_SESSION_ID` |
| `BAEMIN_SESSION_ID`         |
| `BAEMIN_COOKIE`             |


> `__cf_bm` 쿠키는 유효시간이 짧으므로 만료 시 Postman 등에서 최신값을 복사해서 `.env`에 업데이트한다.

---

## API 클라이언트

### `scripts_api/base_api.py`

`COMMON_HEADERS`, `COMMON_PARAMS`를 모듈 레벨 상수로 정의해 하위 클라이언트가 공유합니다.

### `scripts_api/shop_api.py`

#### SortOption


| 상수                    | 값                | 설명      |
| --------------------- | ---------------- | ------- |
| `SortOption.DEFAULT`  | `SORT__DEFAULT`  | 기본순     |
| `SortOption.ORDER`    | `SORT__ORDER`    | 주문 많은 순 |
| `SortOption.FAVORITE` | `SORT__FAVORITE` | 찜 많은 순  |
| `SortOption.DISTANCE` | `SORT__DISTANCE` | 가까운 순   |
| `SortOption.STAR`     | `SORT__STAR`     | 별점 높은 순 |


#### `get_shops(display_category, sort, offset, limit)`

```python
from scripts_api.shop_api import get_shops, SortOption

shops = get_shops("FOOD_CATEGORY_JOKBAL", SortOption.STAR)
```

**주요 응답 필드**


| 경로                                                   | 설명                         |
| ---------------------------------------------------- | -------------------------- |
| `shopInfo.shopName`                                  | 가게 이름                      |
| `shopInfo.shopNumber`                                | 가게 번호                      |
| `shopInfo.minimumOrderPrice`                         | 최소 주문 금액                   |
| `shopStatistics.averageStarScore`                    | 평균 별점                      |
| `shopStatistics.latestReviewCount`                   | 최근 리뷰 수                    |
| `deliveryInfos[0].distancePhrase`                    | 거리 (예: `"1.2km"`)          |
| `logInfo.performanceAdTrackingLog.performanceAdType` | 광고 여부 (`"CPC"` = 광고)       |
| `adInfo.campaignId`                                  | 광고 캠페인 ID (상세 API 호출 시 사용) |
| `contextInfo.bypassData`                             | 상세 API 호출 시 전달하는 컨텍스트      |
| `contextInfo.exposedDeliveryType`                    | 노출 배달 유형 (상세 API 호출 시 사용)  |


### `scripts_api/shop_detail_api.py`

목록 API 응답의 가게 dict를 그대로 받아 상세 정보를 조회합니다.

```python
from scripts_api.shop_detail_api import get_shop_detail

detail = get_shop_detail(shop, sort=SortOption.DEFAULT)
```

목록→상세 전달 필드: `shopInfo.shopNumber`(경로), `adInfo.campaignId`, `contextInfo.bypassData`, `contextInfo.exposedDeliveryType`, `shopInfo.menus[0].menuId`

---

## 테스트 케이스

### `tests_api/test_shop.py` — 목록 API

conftest.py의 session fixture가 API를 호출하고 결과를 JSON으로 저장합니다.

| 테스트                               | fixture          | 검증 내용                             | 결과 요약                              |
| --------------------------------- | ---------------- | --------------------------------- | ---------------------------------- |
| `test_shop_list_count`            | `shops_default`  | 기본 요청(offset=0, limit=30) 시 1개 이상 limit 이하 반환 | 30개 반환                             |
| `test_sort_by_star_descending`    | `shops_star`     | 광고 제외 가게의 `averageStarScore` 내림차순 | 광고 제외 28개, 전체 5.0점 (동점 다수)         |
| `test_sort_by_distance_ascending` | `shops_distance` | 광고 제외 가게의 거리 오름차순                 | 광고 제외 28개, 1.0km ~ 2.2km 오름차순 확인   |
| `test_default_sort_contains_ads`  | `shops_default`  | 기본순 CPC 광고 가게 현황 출력 (assert 없음)   | 광고 가게 7개 확인 (시간대별 변동)              |


### `tests_api/test_shop_detail.py` — 목록↔상세 교차 검증

`shop_details` session fixture가 `shops_default.json`을 로드 → 상세 API 순차 호출 → `shop_details.json` 저장합니다.

| 테스트                                     | 검증 내용                                                         | 결과 요약                    |
| --------------------------------------- | ------------------------------------------------------------- | ------------------------ |
| `test_shop_name_matches_list`           | 상세 `shopName` == 목록 `shopInfo.shopName`                       | 10개 전체 일치                |
| `test_minimum_order_price_matches_list` | 상세 `shopMinimumOrderPrice` == 목록 `shopInfo.minimumOrderPrice` | 10개 전체 일치 (12,000 ~ 30,000원) |
| `test_shop_is_possible_to_order`        | 상세 `isPossibleToOrder == True`                                | 10개 전체 주문 가능 상태          |
| `test_review_rating_matches_list`       | 상세 `reviewRatingText` == 목록 `averageStarScore`                | 10개 전체 일치 (4.5 ~ 5.0)    |


---

## 실행 방법

```bash
# 전체 API 테스트 (목록 API 호출 → assert → JSON 저장 → 상세 API 호출 → assert → JSON 저장)
pytest tests_api/ -v -s

# 목록 테스트만 (shops_default.json 등 생성됨)
pytest tests_api/test_shop.py -v -s

# 상세 교차 검증만 (shops_default.json 사전 필요)
pytest tests_api/test_shop_detail.py -v -s
```

> `test_shop_detail.py` 단독 실행 시 `tests_api/fixtures/shops_default.json`이 있어야 합니다.
> 없으면 `test_shop.py`를 먼저 실행하세요.

---

## TODO

### 스키마 검증 추가

응답 필드의 타입·필수 여부를 검증하는 스키마 테스트를 추가할 예정이다.
값 비교만으로는 필드가 아예 사라지거나 타입이 바뀌는 케이스를 잡을 수 없다.

**구현 방향**
- `jsonschema` 라이브러리 사용
- `scripts_api/schemas.py`에 스키마 정의 분리
- `required` 필드 + 타입 검증 위주 (부분 스키마)
- API 스펙 변경 시 스키마 파일만 수정

**JSON Schema 공부 순서**
1. `type`, `required`, `properties` 기본 3개
2. `null` 타입 처리 — 필드 없음 vs null 구분
3. `enum` — 고정값 검증 (예: `"CPC"`, `"SORT__DEFAULT"`)
4. `additionalProperties` — 불필요한 필드 차단 여부
5. `$ref` — 스키마 재사용 (중복 제거)

> 참고: `json-schema.org` (공식 스펙)

---

## 예외 사항

### 주문순 정렬 (`SORT__ORDER`) 검증 불가

응답의 `logInfo.orderCount` 필드가 항상 `0`을 반환한다.
비로그인 환경에서는 실제 주문 수를 노출하지 않는 것으로 보이며,
`latestReviewCount`를 proxy로 사용해도 주문 수와 1:1 대응이 되지 않아 정렬 순서 자동 검증이 불가능하다.

**결론**: `SORT__ORDER` 정렬 정확도는 자동화 테스트에서 제외, 수동 확인으로 대체한다.

### 찜순 정렬 (`SORT__FAVORITE`) 검증 불가

찜 수에 해당하는 필드가 응답에 포함되어 있지 않아 정렬 순서 검증이 불가능하다.

**결론**: `SORT__FAVORITE` 정렬 정확도는 자동화 테스트에서 제외, 수동 확인으로 대체한다.

### 광고 포함 여부 (`test_default_sort_contains_ads`) 검증 불가

광고는 광고주의 설정 기간·예산에 따라 노출되므로 특정 시간대에는 0개일 수 있다.
assert로 강제하면 광고가 없는 시간대에 테스트가 실패하는 오탐이 발생한다.

**결론**: assert 제거, print로 현황만 출력하는 확인용 테스트로 유지한다.

### 영업 중 여부 (`isPossibleToOrder`) 검증 한계

상세 API 응답에 `isPossibleToOrder` 필드가 존재하나, 목록 API 요청 시 영업 중인 가게만 필터링되는지 확인이 불가능하다.
현재 테스트는 "조회된 상위 10개 가게가 모두 주문 가능 상태인지"만 검증한다.

**결론**: 영업 중 필터링 로직 자체는 자동화 검증 범위 밖이며, 정상 영업 시간대에 실행할 때만 의미 있는 테스트다.

# TODO

## Self-Healing DOM Context 최적화

### 배경
현재 `self_healing.py`의 `_get_element_context()`는 `form/main/body` 순서로 컨테이너를 찾아
최대 4000자를 OpenAI에 전송한다. 로그인 페이지처럼 단순한 페이지는 괜찮지만
검색 결과 등 DOM이 큰 페이지에서는 토큰 낭비가 발생한다.

### 개선 방향
primary, fallback 모두 실패했을 때:

```
primary 실패 → fallback 실패
    → page.evaluate(JS)로 실패한 요소 주변 HTML만 추출 (부모 3단계)
        → 4000자 이내로 OpenAI 전송
            → 새 selector 후보 받아서 순차 시도
                → 성공하면 primary + fallback 둘 다 업데이트
```

### 구현 포인트
- `page.evaluate(JS)`로 DOM 탐색은 브라우저(JS)가 수행, 결과값만 Python으로 반환
- fallback selector가 있으면 그 요소의 부모 3단계 HTML만 추출
- fallback도 없으면 title/placeholder 속성으로 관련 요소 검색 후 주변 추출
- 최후 수단으로 form → main → body 순서 (현재 방식)

### 관련 파일
- `self_healing.py` — `_get_element_context()` 함수 개선
- `scripts/base_page.py` — primary/fallback 모두 실패 시 `try_heal()` 호출 추가
- `locators.json` — fallback 필드 활용

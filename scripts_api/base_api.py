"""
배민 API 공통 헤더 및 파라미터

scripts_api/ 하위 모든 API 클라이언트가 공유하는 기본값.
환경변수는 .env 파일로 관리한다.
"""

import os
from dotenv import load_dotenv

load_dotenv()

COMMON_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "ko",
    "Accept-Encoding": "gzip, deflate",
    "User-Baedal": os.getenv("BAEMIN_USER_BAEDAL", ""),
    "Carrier": "6553565535",
    "User-Agent": "iph1_16.0.1",
    "Cookie": os.getenv("BAEMIN_COOKIE", ""),
}

COMMON_PARAMS = {
    "actionTrackingKey": "4557",
    "adid": "00000000-0000-0000-0000-000000000000",
    "adjustId": os.getenv("BAEMIN_ADJUST_ID", ""),
    "appver": "16.0.1",
    "carrier": "6553565535",
    "deviceModel": "iPhone17,2",
    "dongCode": "11530112",
    "dvc_uniq_id": os.getenv("BAEMIN_DVC_UNIQ_ID", ""),
    "dvcid": os.getenv("BAEMIN_DVCID", ""),
    "idfv": os.getenv("BAEMIN_DVC_UNIQ_ID", ""),
    "latitude": "37.48198901",
    "longitude": "126.82225986",
    "memberNumber": "000000000000",
    "oscd": "1",
    "osver": "18.1",
    "perseusClientId": os.getenv("BAEMIN_PERSEUS_CLIENT_ID", ""),
    "perseusSessionId": os.getenv("BAEMIN_PERSEUS_SESSION_ID", ""),
    "sessionid": os.getenv("BAEMIN_SESSION_ID", ""),
    "site": "7jWXRELC2e",
    "zipCode": "08362",
}

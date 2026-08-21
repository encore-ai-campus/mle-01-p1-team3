from typing import Any

from getpass import getpass
import requests

# 1. 메이플스토리 API 공통 주소

BASE_URL = "https://open.api.nexon.com/maplestory/v1"

ERROR_MESSAGES = {
    # 서버 내부 오류
    "OPENAPI00001": "NEXON Open API 서버 내부 오류가 발생했습니다. "
    "잠시 후 다시 시도해 주세요.",
    # 권한 없음
    "OPENAPI00002": "해당 API를 호출할 권한이 없습니다.",
    # 유효하지 않은 식별자
    "OPENAPI00003": "유효하지 않은 캐릭터 식별자입니다.",
    # 파라미터 누락 / 잘못된 파라미터
    "OPENAPI00004": "API 요청 파라미터가 누락되었거나 올바르지 않습니다.",
    # API Key 오류
    "OPENAPI00005": "유효하지 않은 API Key입니다.",
    # 잘못된 API 주소
    "OPENAPI00006": "유효하지 않은 게임 또는 API 경로입니다.",
    # 호출량 초과
    "OPENAPI00007": "API 호출량을 초과했습니다. " "잠시 후 다시 시도해 주세요.",
    # 데이터 준비 중
    "OPENAPI00009": "데이터가 준비 중입니다. " "잠시 후 다시 조회해 주세요.",
    # 게임 점검
    "OPENAPI00010": "현재 메이플스토리가 점검 중입니다.",
    # API 점검
    "OPENAPI00011": "현재 NEXON Open API가 점검 중입니다.",
}


# ============================================================
# 3. NEXON API 전용 Exception
# ============================================================


class NexonApiError(Exception):
    """
    NEXON API 요청 중 문제가 발생했을 때 사용하는 공통 오류 클래스.

    나중에 Streamlit에서도 그대로 사용할 수 있음.

    예)

    try:
        ...
    except NexonApiError as e:
        st.error(e.user_message)
    """

    def __init__(
        self,
        user_message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        original_message: str | None = None,
    ):

        # 일반 Exception 메시지
        super().__init__(user_message)

        # 사용자에게 보여줄 메시지
        self.user_message = user_message

        # HTTP 상태 코드
        # 예: 400, 403, 429, 500, 503
        self.status_code = status_code

        # NEXON 오류 코드
        # 예: OPENAPI00007
        self.error_code = error_code

        # NEXON 서버가 실제로 반환한 원본 메시지
        self.original_message = original_message


# ============================================================
# 4. NEXON API Client
# ============================================================


class NexonClient:

    def __init__(
        self,
        api_key: str,
        timeout: float = 10,
    ):
        """
        NexonClient 생성

        Parameters
        ----------
        api_key : str
            NEXON Open API Key

        timeout : float
            API 응답을 기다릴 최대 시간(초)
            기본값 = 10초
        """

        # API Key가 비어 있는 경우
        if not api_key or not api_key.strip():

            raise ValueError("API Key가 비어 있습니다.")

        self.api_key = api_key.strip()

        self.timeout = timeout

        # requests.Session 사용
        #
        # 일반 requests.get()을 계속 사용하는 것보다
        # HTTP 연결을 재사용할 수 있음
        self.session = requests.Session()

    # ========================================================
    # 5. 공통 GET 요청 함수
    # ========================================================

    def _get(
        self,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        실제 API 요청을 담당하는 공통 함수.

        get_ocid()
        get_basic()
        get_stat()
        ...

        모두 내부적으로 이 함수를 사용합니다.
        """

        # 최종 URL 생성
        #
        # ex)
        #
        # BASE_URL
        # https://open.api.nexon.com/maplestory/v1
        #
        # path
        # /id
        #
        # 결과
        # https://open.api.nexon.com/maplestory/v1/id

        url = f"{BASE_URL}{path}"

        # NEXON API Key는 HTTP Header에 전달
        headers = {
            "x-nxopen-api-key": self.api_key,
            "Accept": "application/json",
        }

        # ====================================================
        # 실제 HTTP 요청
        # ====================================================

        try:

            response = self.session.get(
                url=url,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )

        # ----------------------------------------------------
        # API 서버 응답 시간이 timeout을 넘긴 경우
        # ----------------------------------------------------

        except requests.Timeout as error:

            raise NexonApiError(
                "API 응답 시간이 초과되었습니다. " "잠시 후 다시 시도해 주세요.",
                original_message=str(error),
            ) from error

        # ----------------------------------------------------
        # 인터넷 연결 실패 / 서버 연결 실패
        # ----------------------------------------------------

        except requests.ConnectionError as error:

            raise NexonApiError(
                "NEXON API 서버에 연결할 수 없습니다. "
                "네트워크 상태를 확인해 주세요.",
                original_message=str(error),
            ) from error

        # ----------------------------------------------------
        # 그 외 requests 라이브러리 관련 오류
        # ----------------------------------------------------

        except requests.RequestException as error:

            raise NexonApiError(
                "API 요청 중 네트워크 오류가 발생했습니다.",
                original_message=str(error),
            ) from error

        # ====================================================
        # JSON 변환
        # ====================================================

        try:

            data = response.json()

        except ValueError as error:

            # 서버 응답은 왔지만 JSON이 아닐 경우
            raise NexonApiError(
                "API 응답을 JSON 형식으로 해석하지 못했습니다.",
                status_code=response.status_code,
                original_message=str(error),
            ) from error

        # ====================================================
        # 정상 응답
        # ====================================================

        if response.status_code == 200:

            # 정상 API는 JSON object 형태를 기대
            if not isinstance(data, dict):

                raise NexonApiError(
                    "API 응답 형식이 예상과 다릅니다.",
                    status_code=response.status_code,
                )

            return data

        # ====================================================
        # API 오류 응답 처리
        # ====================================================
        #
        # 예상 구조
        #
        # {
        #     "error": {
        #         "name": "OPENAPI00007",
        #         "message": "API call limit exceeded"
        #     }
        # }
        # ====================================================

        if isinstance(data, dict):

            error_data = data.get("error", {})

        else:

            error_data = {}

        if isinstance(error_data, dict):

            error_code = error_data.get("name")

            original_message = error_data.get("message")

        else:

            error_code = None
            original_message = None

        # 공식 오류 코드에 정의되어 있으면
        # 우리가 만든 한국어 메시지 사용
        user_message = ERROR_MESSAGES.get(error_code)

        # 정의되지 않은 오류라면
        # NEXON 원본 오류 메시지를 사용
        if user_message is None:

            user_message = (
                original_message
                or f"API 요청에 실패했습니다. "
                f"HTTP 상태 코드: {response.status_code}"
            )

        # 최종적으로 NexonApiError 발생
        raise NexonApiError(
            user_message,
            status_code=response.status_code,
            error_code=error_code,
            original_message=original_message,
        )

    # ========================================================
    # 6. 캐릭터명 -> OCID 조회
    # ========================================================

    def get_ocid(
        self,
        character_name: str,
    ) -> str:
        """
        캐릭터 닉네임으로 OCID 조회.

        이후 캐릭터 정보 API들은
        대부분 OCID를 사용합니다.
        """

        # 캐릭터명이 비어 있으면 API 요청하지 않음
        if not character_name or not character_name.strip():

            raise ValueError("캐릭터명을 입력해 주세요.")

        # GET /maplestory/v1/id

        data = self._get(
            "/id",
            {"character_name": character_name.strip()},
        )

        # 정상 응답 예시
        #
        # {
        #     "ocid": "..."
        # }

        ocid = data.get("ocid")

        # 200 응답인데 ocid가 없는 비정상 상황
        if not ocid:

            raise NexonApiError("정상 응답에서 OCID를 찾지 못했습니다.")

        return ocid

    # ========================================================
    # 7. 캐릭터 기본 정보
    # ========================================================

    def get_basic(
        self,
        ocid: str,
    ) -> dict[str, Any]:
        """
        캐릭터 기본 정보 조회.

        캐릭터명
        월드
        직업
        레벨
        경험치
        길드
        캐릭터 이미지
        등을 받을 수 있음.
        """

        return self._get(
            "/character/basic",
            {"ocid": ocid},
        )

    # ========================================================
    # 아래 함수들은 지금 당장 테스트하지 않아도 됨.
    #
    # 이후 Streamlit에서
    # 장비 / 스탯 / 심볼 / 유니온 탭을 만들 때
    # 그대로 사용할 수 있도록 미리 만들어 둠.
    # ========================================================

    # ========================================================
    # 8. 종합 능력치
    # ========================================================

    def get_stat(
        self,
        ocid: str,
    ) -> dict[str, Any]:

        return self._get(
            "/character/stat",
            {"ocid": ocid},
        )

    # ========================================================
    # 9. 현재 장착 장비
    # ========================================================

    def get_equipment(
        self,
        ocid: str,
    ) -> dict[str, Any]:

        return self._get(
            "/character/item-equipment",
            {"ocid": ocid},
        )

    # ========================================================
    # 10. 심볼
    # ========================================================

    def get_symbols(
        self,
        ocid: str,
    ) -> dict[str, Any]:

        return self._get(
            "/character/symbol-equipment",
            {"ocid": ocid},
        )

    # ========================================================
    # 11. 유니온
    # ========================================================

    def get_union(
        self,
        ocid: str,
    ) -> dict[str, Any]:

        return self._get(
            "/user/union",
            {"ocid": ocid},
        )
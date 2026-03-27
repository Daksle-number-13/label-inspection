from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Vision API
    google_vision_api_key: str = ""

    # 클라우디아크 공유링크 (기준값 엑셀)
    standards_excel_url: str = ""
    # 기준값 캐시 유효시간 (초, 기본 1시간)
    standards_cache_ttl: int = 3600

    # 카카오 알림톡 (NHN Cloud / BizPPURIO 등 공급사 공통 포맷)
    kakao_api_key: str = ""
    kakao_api_url: str = ""          # 공급사 API 엔드포인트
    kakao_sender_key: str = ""       # 플러스친구 발신 프로필 키
    kakao_template_code: str = ""    # 등록된 템플릿 코드
    kakao_receiver_phone: str = ""   # 파트장 수신 전화번호

    # CORS 허용 출처 (프론트엔드 URL)
    allowed_origins: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()

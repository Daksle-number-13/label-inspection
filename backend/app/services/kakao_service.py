"""
카카오 알림톡 발송 서비스
- NHN Cloud / BizPPURIO 등 공급사 API 연동 (공통 포맷)
- 불량 확정 시 파트장에게 자동 알림
"""
import logging
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _build_message(defects: list[dict], inspector: str, product_info: str) -> str:
    """알림톡 본문 구성."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"[박스라벨 불량 알림]",
        f"검사일시: {now}",
        f"검사자: {inspector}",
        f"제품정보: {product_info}",
        f"",
        f"▶ 불량 항목 ({len(defects)}건)",
    ]
    for d in defects:
        lines.append(f"  · {d['field']}: 기준[{d['expected']}] / 실제[{d.get('found', '미확인')}]")
    lines.append("")
    lines.append("즉시 확인 후 조치 바랍니다.")
    return "\n".join(lines)


async def send_defect_alert(
    defects: list[dict],
    inspector: str = "검사자",
    product_info: str = "",
) -> dict:
    """
    불량 항목을 파트장에게 카카오 알림톡으로 발송.
    반환: {"success": bool, "message": str}
    """
    if not settings.kakao_api_key or not settings.kakao_api_url:
        logger.warning("카카오 알림톡 설정 미완료 — 발송 건너뜀")
        return {"success": False, "message": "카카오 알림톡 설정이 완료되지 않았습니다."}

    if not settings.kakao_receiver_phone:
        return {"success": False, "message": "수신자 전화번호(KAKAO_RECEIVER_PHONE)가 설정되지 않았습니다."}

    message = _build_message(defects, inspector, product_info)

    # 공급사 공통 페이로드 (NHN Cloud 기준, BizPPURIO 등 유사 포맷)
    payload = {
        "senderKey": settings.kakao_sender_key,
        "templateCode": settings.kakao_template_code,
        "recipientList": [
            {
                "recipientNo": settings.kakao_receiver_phone,
                "templateParameter": {
                    "inspector": inspector,
                    "product_info": product_info,
                    "defect_count": str(len(defects)),
                    "defect_detail": message,
                },
                "content": message,
            }
        ],
    }

    headers = {
        "X-Secret-Key": settings.kakao_api_key,
        "Content-Type": "application/json;charset=UTF-8",
    }

    logger.info("카카오 알림톡 발송 시도: %s → 불량 %d건", settings.kakao_receiver_phone, len(defects))

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(settings.kakao_api_url, json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()
        logger.info("카카오 알림톡 발송 성공: %s", result)
        return {"success": True, "message": "알림톡 발송 완료", "detail": result}
    except httpx.HTTPStatusError as e:
        logger.error("카카오 알림톡 발송 실패: %s", e.response.text)
        return {"success": False, "message": f"발송 실패: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        logger.error("카카오 알림톡 예외: %s", str(e))
        return {"success": False, "message": f"발송 중 오류: {str(e)}"}

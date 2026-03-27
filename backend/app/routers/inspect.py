"""
라벨 검사 라우터
- 이미지 업로드 → OCR → 기준값 대조 → 결과 반환
"""
import re
import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import vision_service, standards_service, kakao_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inspect", tags=["검사"])


def _normalize(text: str) -> str:
    """비교를 위한 텍스트 정규화 (공백·특수문자 제거, 소문자화)."""
    return re.sub(r"[\s\-_/]", "", text).lower()


def _find_in_ocr(expected: str, ocr_text: str, lines: list[str]) -> dict:
    """
    OCR 결과에서 기준값을 탐색.
    반환: {"found": bool, "matched_text": str, "context": str}
    """
    norm_expected = _normalize(expected)
    norm_full = _normalize(ocr_text)

    # 정규화 후 완전 포함 여부
    if norm_expected and norm_expected in norm_full:
        # 원본 라인에서 기준값이 포함된 라인 찾기
        for line in lines:
            if norm_expected in _normalize(line):
                return {"found": True, "matched_text": expected, "context": line.strip()}
        return {"found": True, "matched_text": expected, "context": ""}

    # 유사 탐색: 기준값 앞뒤 단어 비교로 근접값 추출
    best_context = ""
    for line in lines:
        if expected.lower() in line.lower():
            return {"found": True, "matched_text": expected, "context": line.strip()}
        # 부분 매칭 (길이 >= 3인 경우)
        if len(expected) >= 3 and any(
            _normalize(expected[:i]) in _normalize(line) for i in range(3, len(expected) + 1)
        ):
            best_context = line.strip()

    if best_context:
        return {"found": False, "matched_text": "", "context": best_context}

    return {"found": False, "matched_text": "", "context": ""}


@router.post("/", summary="라벨 이미지 검사")
async def inspect_label(
    file: UploadFile = File(..., description="박스라벨 이미지 (JPEG/PNG)"),
    inspector: str = Form(default="검사자", description="검사자 이름"),
    product_info: str = Form(default="", description="제품 정보 메모"),
    send_alert: bool = Form(default=False, description="불량 시 알림톡 자동 발송"),
):
    """
    라벨 이미지를 업로드하면 OCR 후 기준값과 자동 대조합니다.
    불량 항목이 있고 send_alert=true 이면 파트장에게 카카오 알림톡을 발송합니다.
    """
    # --- 1. 이미지 읽기 ---
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="이미지 파일이 비어 있습니다.")

    # --- 2. OCR ---
    try:
        ocr_result = await vision_service.extract_text(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 실패: {str(e)}")

    # --- 3. 기준값 로드 ---
    try:
        standards = await standards_service.get_standards()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"기준값 로드 실패: {str(e)}")

    # --- 4. 대조 ---
    results = []
    defects = []

    for std in standards:
        field = std["field"]
        expected = std["expected"]
        notes = std.get("notes", "")

        match_info = _find_in_ocr(expected, ocr_result["full_text"], ocr_result["lines"])
        is_pass = match_info["found"]

        item = {
            "field": field,
            "expected": expected,
            "found": match_info["matched_text"] if is_pass else match_info["context"] or "미확인",
            "context": match_info["context"],
            "status": "pass" if is_pass else "fail",
            "notes": notes,
        }
        results.append(item)
        if not is_pass:
            defects.append(item)

    total = len(results)
    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = total - pass_count
    overall = "pass" if fail_count == 0 else "fail"

    # --- 5. 알림톡 발송 ---
    alert_result = None
    if send_alert and defects:
        alert_result = await kakao_service.send_defect_alert(
            defects=defects,
            inspector=inspector,
            product_info=product_info,
        )

    logger.info(
        "검사 완료: 검사자=%s, 전체=%d, 합격=%d, 불량=%d, 판정=%s",
        inspector, total, pass_count, fail_count, overall,
    )

    return {
        "overall": overall,
        "summary": {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "inspector": inspector,
            "product_info": product_info,
        },
        "results": results,
        "defects": defects,
        "ocr": {
            "full_text": ocr_result["full_text"],
            "lines": ocr_result["lines"],
        },
        "alert": alert_result,
    }


@router.post("/alert", summary="불량 알림톡 수동 발송")
async def send_alert_manual(body: dict):
    """
    불량 항목 목록을 받아 파트장에게 카카오 알림톡을 발송합니다.
    body: { defects: [...], inspector: str, product_info: str }
    """
    defects = body.get("defects", [])
    if not defects:
        raise HTTPException(status_code=400, detail="불량 항목이 없습니다.")

    result = await kakao_service.send_defect_alert(
        defects=defects,
        inspector=body.get("inspector", "검사자"),
        product_info=body.get("product_info", ""),
    )
    return result

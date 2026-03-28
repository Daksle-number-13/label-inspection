"""
라벨 검사 라우터 — 강화된 OCR 판정 엔진
=========================================
판정 방식 (우선순위 순):
  1. 필드명 기반 값 추출  → 라벨의 "제품코드: ABC-1234" 에서 "ABC-1234" 추출 후 비교
  2. 정규화 완전 일치      → 공백·특수문자 제거 후 포함 여부
  3. 유사도(Levenshtein)  → 설정된 임계값(기본 0.85) 이상이면 합격
  4. 한글 OCR 오인식 보정 → ㅇ↔0, ㅣ↔1 등 흔한 오인식 교정 후 재비교

기준값 엑셀 확장 컬럼 (standards_service 와 연동):
  A=검사항목, B=기준값, C=필수여부(Y/N), D=허용오차, E=매칭방식, F=비고
"""
import re
import logging
from datetime import datetime
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import vision_service, standards_service, kakao_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inspect", tags=["검사"])

# 유사도 판정 임계값 (0~1, 기본 85%)
SIMILARITY_THRESHOLD = 0.85

# 한글 OCR 흔한 오인식 교정 테이블
_OCR_CORRECTIONS: dict[str, str] = {
    # 한글 자모 → 숫자/기호
    "ㅇ": "0", "ㅣ": "1", "ㄱ": "7", "ㅡ": "-",
    # 전각 숫자 → 반각
    "０": "0", "１": "1", "２": "2", "３": "3",
    "４": "4", "５": "5", "６": "6", "７": "7",
    "８": "8", "９": "9",
    # 전각 알파벳 → 반각
    "Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D", "Ｅ": "E",
    "Ｆ": "F", "Ｇ": "G", "Ｈ": "H", "Ｉ": "I", "Ｊ": "J",
    "Ｋ": "K", "Ｌ": "L", "Ｍ": "M", "Ｎ": "N", "Ｏ": "O",
    "Ｐ": "P", "Ｑ": "Q", "Ｒ": "R", "Ｓ": "S", "Ｔ": "T",
    "Ｕ": "U", "Ｖ": "V", "Ｗ": "W", "Ｘ": "X", "Ｙ": "Y", "Ｚ": "Z",
    # 특수 유사 문자
    "Ｏ": "O", "ｌ": "l", "Ｉ": "I",
    # 영문↔숫자 혼동 (OCR 자주 발생)
    "O": "0",  # 필요시 활성화
}

# 날짜 패턴 정규식 (다양한 구분자 허용)
_DATE_PATTERN = re.compile(r"\d{2,4}[\-./년]\d{1,2}[\-./월]\d{2}일?")


# ── 유틸 함수 ──────────────────────────────────────────────────────────────

def _correct_ocr(text: str) -> str:
    """흔한 OCR 오인식 문자를 교정."""
    for wrong, right in _OCR_CORRECTIONS.items():
        text = text.replace(wrong, right)
    return text


def _normalize(text: str) -> str:
    """비교용 정규화: 공백·구분자 제거, 소문자화, OCR 오인식 교정."""
    text = _correct_ocr(text)
    return re.sub(r"[\s\-_/.:·•,]", "", text).lower()


def _levenshtein_similarity(a: str, b: str) -> float:
    """두 문자열의 Levenshtein 유사도 반환 (0.0 ~ 1.0)."""
    if not a or not b:
        return 0.0
    a, b = _normalize(a), _normalize(b)
    if a == b:
        return 1.0
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0.0
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return round(1.0 - dp[n] / max(m, n), 4)


def _extract_by_fieldname(field: str, lines: list[str]) -> str:
    """
    OCR 라인에서 '필드명: 값' 또는 '필드명 값' 패턴으로 값 추출.
    라벨에 'LOT NO: L20260301' 형식이 있으면 'L20260301' 반환.
    """
    norm_field = _normalize(field)
    for line in lines:
        if norm_field in _normalize(line):
            # 구분자(콜론, 등호, 공백) 이후 값 추출
            for sep in [":", "：", "=", "·", " "]:
                idx = line.find(sep)
                if idx != -1:
                    value = line[idx + 1 :].strip()
                    if value:
                        return value
    return ""


def _check_tolerance(expected: str, actual: str, tolerance: str) -> bool:
    """
    허용 오차 범위 검사.
    tolerance 예시: '±5%', '±2', '±0.5'
    """
    try:
        exp_num = float(re.sub(r"[^\d.]", "", expected))
        act_num = float(re.sub(r"[^\d.]", "", actual))
        tol_str = tolerance.replace("±", "").strip()
        if "%" in tol_str:
            tol = exp_num * float(tol_str.replace("%", "")) / 100
        else:
            tol = float(tol_str)
        return abs(exp_num - act_num) <= tol
    except (ValueError, ZeroDivisionError):
        return False


def _match(
    expected: str,
    ocr_full: str,
    ocr_lines: list[str],
    field_name: str,
    match_type: str,
    tolerance: str,
) -> dict:
    """
    단일 항목 판정.
    반환: {
        "passed": bool,
        "method": str,          # 판정에 사용된 방법
        "similarity": float,    # 유사도 (0~1)
        "extracted": str,       # OCR에서 추출된 실제값
        "context": str,         # 해당 라인 전체
    }
    """
    if not expected:
        return {"passed": True, "method": "skip_empty", "similarity": 1.0, "extracted": "", "context": ""}

    # ── 방법 1: 필드명 기반 값 추출 후 비교 ──────────────────
    extracted = _extract_by_fieldname(field_name, ocr_lines)
    if extracted:
        if tolerance:
            if _check_tolerance(expected, extracted, tolerance):
                return {"passed": True, "method": "field+tolerance", "similarity": 1.0, "extracted": extracted, "context": extracted}
        sim = _levenshtein_similarity(expected, extracted)
        if sim >= SIMILARITY_THRESHOLD:
            return {"passed": True, "method": "field+similarity", "similarity": sim, "extracted": extracted, "context": extracted}

    # ── 방법 2: 정규화 완전 포함 ─────────────────────────────
    norm_exp = _normalize(expected)
    norm_full = _normalize(ocr_full)
    if norm_exp and norm_exp in norm_full:
        context = next((l for l in ocr_lines if norm_exp in _normalize(l)), "")
        return {"passed": True, "method": "normalized_contains", "similarity": 1.0, "extracted": expected, "context": context}

    # ── 방법 3: 유사도 기반 라인별 비교 ─────────────────────
    best_sim, best_ctx = 0.0, ""
    for line in ocr_lines:
        sim = _levenshtein_similarity(expected, line)
        if sim > best_sim:
            best_sim, best_ctx = sim, line
        # 라인에서 부분 추출해서 비교
        words = re.split(r"[\s:：=·]+", line)
        for word in words:
            ws = _levenshtein_similarity(expected, word)
            if ws > best_sim:
                best_sim, best_ctx = ws, line

    if best_sim >= SIMILARITY_THRESHOLD:
        return {"passed": True, "method": "fuzzy", "similarity": best_sim, "extracted": best_ctx.strip(), "context": best_ctx.strip()}

    # ── 방법 4: regex 매칭 (매칭방식='regex' 일 때) ──────────
    if match_type == "regex":
        try:
            if re.search(expected, ocr_full, re.IGNORECASE):
                return {"passed": True, "method": "regex", "similarity": 1.0, "extracted": expected, "context": ""}
        except re.error:
            pass

    # ── 판정 실패 ────────────────────────────────────────────
    return {
        "passed": False,
        "method": "no_match",
        "similarity": best_sim,
        "extracted": best_ctx.strip() if best_ctx else "미인식",
        "context": best_ctx.strip(),
    }


# ── 라우터 ──────────────────────────────────────────────────────────────────

@router.post("/", summary="라벨 이미지 검사")
async def inspect_label(
    file: UploadFile = File(..., description="박스라벨 이미지 (JPEG/PNG)"),
    inspector: str = Form(default="검사자", description="검사자 이름"),
    product_info: str = Form(default="", description="제품 정보 메모"),
    send_alert: bool = Form(default=False, description="불량 시 알림톡 자동 발송"),
):
    """
    라벨 이미지를 업로드하면 OCR 후 기준값과 자동 대조합니다.
    """
    # 1. 이미지 읽기
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="이미지 파일이 비어 있습니다.")

    # 2. OCR
    try:
        ocr_result = await vision_service.extract_text(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 실패: {str(e)}")

    # 3. 기준값 로드
    try:
        standards = await standards_service.get_standards()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"기준값 로드 실패: {str(e)}")

    # 4. 항목별 대조
    results, defects = [], []

    for std in standards:
        field      = std["field"]
        expected   = std["expected"]
        required   = std.get("required", True)
        tolerance  = std.get("tolerance", "")
        match_type = std.get("match_type", "contains")
        notes      = std.get("notes", "")

        m = _match(expected, ocr_result["full_text"], ocr_result["lines"], field, match_type, tolerance)

        status = "pass" if m["passed"] else ("warn" if not required else "fail")

        item = {
            "field":      field,
            "expected":   expected,
            "found":      m["extracted"],
            "context":    m["context"],
            "status":     status,
            "method":     m["method"],
            "similarity": m["similarity"],
            "required":   required,
            "tolerance":  tolerance,
            "notes":      notes,
        }
        results.append(item)
        if status == "fail":
            defects.append(item)

    total      = len(results)
    pass_count = sum(1 for r in results if r["status"] == "pass")
    warn_count = sum(1 for r in results if r["status"] == "warn")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    overall    = "pass" if fail_count == 0 else "fail"

    # 5. 알림톡 발송
    alert_result = None
    if send_alert and defects:
        alert_result = await kakao_service.send_defect_alert(
            defects=defects,
            inspector=inspector,
            product_info=product_info,
        )

    logger.info(
        "[검사] 검사자=%s | 전체=%d 합격=%d 경고=%d 불량=%d | 판정=%s",
        inspector, total, pass_count, warn_count, fail_count, overall,
    )

    return {
        "overall": overall,
        "inspected_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total":        total,
            "pass":         pass_count,
            "warn":         warn_count,
            "fail":         fail_count,
            "inspector":    inspector,
            "product_info": product_info,
        },
        "results": results,
        "defects": defects,
        "ocr": {
            "full_text": ocr_result["full_text"],
            "lines":     ocr_result["lines"],
        },
        "alert": alert_result,
    }


@router.post("/alert", summary="불량 알림톡 수동 발송")
async def send_alert_manual(body: dict):
    defects = body.get("defects", [])
    if not defects:
        raise HTTPException(status_code=400, detail="불량 항목이 없습니다.")
    return await kakao_service.send_defect_alert(
        defects=defects,
        inspector=body.get("inspector", "검사자"),
        product_info=body.get("product_info", ""),
    )

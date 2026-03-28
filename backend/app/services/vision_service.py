"""
Google Vision API OCR 서비스
- REST API (API Key 방식) 사용
- 이미지에서 텍스트 추출
- 한글/영문/숫자 혼용 라벨 지원
"""
import base64
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"


async def extract_text(image_bytes: bytes) -> dict:
    """
    이미지 바이트를 받아 OCR 텍스트 추출.
    반환: {
        "full_text": "전체 텍스트",
        "lines": ["라인1", "라인2", ...],
        "words": ["단어1", "단어2", ...]
    }
    """
    # ── 개발/테스트용 목업 (API 키 없을 때) ──────────────────
    # 실제 운영 시 아래 블록을 삭제하거나 주석 처리하세요.
    if not settings.google_vision_api_key:
        logger.warning("GOOGLE_VISION_API_KEY 미설정 → 목업 OCR 결과 반환 (테스트 전용)")
        mock_text = (
            "제품코드: ABC-1234\n"
            "로트번호: L20260301\n"
            "수량: 100EA\n"
            "중량: 500g\n"
            "유통기한: 2027-03-01"
        )
        lines = [l for l in mock_text.split("\n") if l]
        return {"full_text": mock_text, "lines": lines, "words": []}
    # ─────────────────────────────────────────────────────────

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [
                    {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}
                ],
                "imageContext": {
                    "languageHints": ["ko", "en"]
                }
            }
        ]
    }

    url = f"{VISION_API_URL}?key={settings.google_vision_api_key}"
    logger.info("Google Vision API 호출 중...")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    response = data.get("responses", [{}])[0]

    if "error" in response:
        raise RuntimeError(f"Vision API 오류: {response['error'].get('message', '알 수 없는 오류')}")

    full_text_annotation = response.get("fullTextAnnotation", {})
    full_text = full_text_annotation.get("text", "").strip()

    # 라인별 텍스트 파싱
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    # 단어 목록
    words = []
    for page in full_text_annotation.get("pages", []):
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                for word in paragraph.get("words", []):
                    word_text = "".join(
                        s.get("text", "") for s in word.get("symbols", [])
                    )
                    if word_text.strip():
                        words.append(word_text.strip())

    logger.info("OCR 완료: 전체 텍스트 %d자, %d 라인, %d 단어", len(full_text), len(lines), len(words))

    return {
        "full_text": full_text,
        "lines": lines,
        "words": words,
    }

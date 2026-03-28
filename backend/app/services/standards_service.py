"""
기준값 서비스
- 클라우디아크 공유링크에서 엑셀 파일을 다운로드
- openpyxl로 파싱하여 메모리 캐싱
- 캐시 TTL 초과 시 자동 갱신
"""
import io
import time
import logging
from typing import Optional

import httpx
import openpyxl

from app.config import settings

logger = logging.getLogger(__name__)

# 메모리 캐시
_cache: list[dict] = []
_cache_loaded_at: float = 0.0


def _is_cache_valid() -> bool:
    if not _cache:
        return False
    return (time.time() - _cache_loaded_at) < settings.standards_cache_ttl


def _parse_excel(content: bytes) -> list[dict]:
    """
    엑셀 파일을 파싱하여 기준값 목록 반환.
    예상 컬럼: A=검사항목, B=기준값, C=비고
    헤더 행(1행)은 건너뜀.
    """
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    standards = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # 헤더 행 스킵
        if not row or row[0] is None:
            continue
        field = str(row[0]).strip()
        value = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        notes = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
        if field:
            standards.append({"field": field, "expected": value, "notes": notes})
    wb.close()
    return standards


async def fetch_and_cache() -> list[dict]:
    """공유링크에서 엑셀을 내려받아 캐시에 저장."""
    global _cache, _cache_loaded_at

    url = settings.standards_excel_url
    if not url:
        # ── 개발/테스트용 목업 기준값 ──────────────────────────
        logger.warning("STANDARDS_EXCEL_URL 미설정 → 목업 기준값 사용 (테스트 전용)")
        _cache = [
            {"field": "제품코드",  "expected": "ABC-1234",    "notes": ""},
            {"field": "로트번호",  "expected": "L20260301",   "notes": ""},
            {"field": "수량",      "expected": "100EA",       "notes": ""},
            {"field": "중량",      "expected": "500g",        "notes": ""},
            {"field": "유통기한",  "expected": "2027-03-01",  "notes": ""},
        ]
        _cache_loaded_at = time.time()
        return _cache
        # ──────────────────────────────────────────────────────

    logger.info("기준값 엑셀 다운로드 시작: %s", url)
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    _cache = _parse_excel(resp.content)
    _cache_loaded_at = time.time()
    logger.info("기준값 캐시 갱신 완료: %d 항목", len(_cache))
    return _cache


async def get_standards(force_refresh: bool = False) -> list[dict]:
    """캐시된 기준값 반환 (만료 시 자동 갱신)."""
    if force_refresh or not _is_cache_valid():
        return await fetch_and_cache()
    return _cache


def get_cache_info() -> dict:
    return {
        "count": len(_cache),
        "loaded_at": _cache_loaded_at,
        "valid": _is_cache_valid(),
        "ttl_remaining": max(0, int(settings.standards_cache_ttl - (time.time() - _cache_loaded_at))),
    }

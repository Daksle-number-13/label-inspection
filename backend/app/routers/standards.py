from fastapi import APIRouter, HTTPException

from app.services import standards_service

router = APIRouter(prefix="/standards", tags=["기준값"])


@router.get("/", summary="기준값 목록 조회")
async def get_standards():
    """캐시된 기준값을 반환합니다. 캐시가 없거나 만료된 경우 자동 갱신합니다."""
    try:
        standards = await standards_service.get_standards()
        return {"standards": standards, "cache": standards_service.get_cache_info()}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기준값 로드 실패: {str(e)}")


@router.post("/refresh", summary="기준값 강제 갱신")
async def refresh_standards():
    """클라우디아크 공유링크에서 엑셀을 다시 내려받아 기준값을 갱신합니다."""
    try:
        standards = await standards_service.get_standards(force_refresh=True)
        return {
            "message": f"기준값 갱신 완료 ({len(standards)}개 항목)",
            "standards": standards,
            "cache": standards_service.get_cache_info(),
        }
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기준값 갱신 실패: {str(e)}")


@router.get("/cache-info", summary="캐시 상태 조회")
async def cache_info():
    return standards_service.get_cache_info()

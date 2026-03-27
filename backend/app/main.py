import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import inspect, standards

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="박스라벨 AI 검사 시스템",
    description="Google Vision OCR + 기준값 자동 대조 + 카카오 알림톡",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inspect.router)
app.include_router(standards.router)


@app.get("/health", tags=["시스템"])
async def health():
    return {"status": "ok", "version": "1.0.0"}

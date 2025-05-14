# app/main.py
from fastapi import FastAPI
from app.routers.infer import router as infer_router

app = FastAPI(
    title="Talent Inference API",
    description="상세 이력서에서 경험·역량 태그를 추론하는 API (한국어)",
    version="0.1.0"
)

app.include_router(infer_router)


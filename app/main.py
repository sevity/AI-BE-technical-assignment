# app/main.py
from fastapi import FastAPI
from app.routers.infer import router as infer_router

app = FastAPI(
    title="Talent Inference API",
    description="Infer skills & experiences from career history via LLM + pgvector",
    version="0.1.0"
)

app.include_router(infer_router)


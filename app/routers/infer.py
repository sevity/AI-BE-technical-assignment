# app/routers/infer.py
from fastapi import APIRouter, HTTPException
from app.schemas import TalentInput, TagResponse
from app.services.inference import InferenceService

router = APIRouter()

@router.post("/infer", response_model=TagResponse)
def infer(payload: TalentInput):
    # 1) 배열 길이 검증
    n = len(payload.company)
    if not (len(payload.period) == n == len(payload.title)):
        raise HTTPException(
            status_code=400,
            detail="company, period, title 리스트는 같은 길이여야 합니다."
        )
    # 2) InferenceService 호출
    try:
        svc = InferenceService()
        return svc.run(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


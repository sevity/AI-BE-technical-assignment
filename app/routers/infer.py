# app/routers/infer.py
from fastapi import APIRouter, HTTPException
from app.schemas import DetailedTalentInput, TagResponse
from app.services.inference import InferenceService

router = APIRouter()

@router.post("/infer", response_model=TagResponse)
def infer(payload: DetailedTalentInput):
    # positions 최소 1건 이상
    if not payload.positions:
        raise HTTPException(status_code=400, detail="positions 리스트가 비어있습니다.")
    # 호출
    try:
        svc = InferenceService()
        return svc.run(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


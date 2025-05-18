# app/routers/infer.py

from fastapi import APIRouter, Depends, HTTPException
from app.schemas import DetailedTalentInput, TagResponse
from app.services.inference import InferenceService
from app.deps import get_openai_client, get_vector_search

router = APIRouter()

@router.post(
    "/infer",
    response_model=TagResponse,
    summary="지원자 경험·역량 태그 추론",
    request_body={
        "content": {
            "application/json": {
                "example": DetailedTalentInput.Config.schema_extra["example"]
            }
        }
    },
)
async def infer(
    payload: DetailedTalentInput,
    openai_client=Depends(get_openai_client),
    vsearch=Depends(get_vector_search),
):
    # positions 최소 1건 이상 검증
    if not payload.positions:
        raise HTTPException(status_code=400, detail="positions 리스트가 비어있습니다.")
    # 호출
    try:
        svc = InferenceService(llm_client=openai_client, vector_search=vsearch)
        return await svc.run(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

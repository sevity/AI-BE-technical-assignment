# app/routers/infer.py

from fastapi import APIRouter, Depends, HTTPException, Body
from app.schemas import DetailedTalentInput, TagResponse
from app.services.inference import InferenceService
from app.deps import get_openai_client, get_vector_search

router = APIRouter()

@router.post(
    "/infer",
    response_model=TagResponse,
    summary="지원자 경험·역량 태그 추론",
    responses={
        200: {
            "description": "태그 추론 성공",
            "content": {
                "application/json": {
                    "example": {
                        "tags": [
                            "상위권대학교 (연세대학교)",
                            "스타트업 성장 경험 (토스 2017–2019)"
                        ]
                    }
                }
            }
        },
        422: {
            "description": "유효성 검사 실패 (입력 스키마 위반)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "positions"],
                                "msg": "ensure this value has at least 1 items",
                                "type": "value_error.list.min_items"
                            }
                        ]
                    }
                }
            }
        },
        400: {
            "description": "비즈니스 로직 에러",
            "content": {
                "application/json": {
                    "example": {"detail": "positions 리스트가 비어있습니다."}
                }
            }
        },
        500: {
            "description": "서버 내부 오류"
        }
    },
)
async def infer(
    payload: DetailedTalentInput = Body(
        ...,
        example=DetailedTalentInput.Config.json_schema_extra["example"]
    ),
    openai_client=Depends(get_openai_client),
    vsearch=Depends(get_vector_search),
):
    # positions 최소 1건 이상 검증
    if not payload.positions:
        raise HTTPException(status_code=400, detail="positions 리스트가 비어있습니다.")
    # 서비스 호출
    try:
        svc = InferenceService(llm_client=openai_client, vector_search=vsearch)
        return await svc.run(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

from pydantic import BaseModel, Field
from typing import List, Optional

class DateInfo(BaseModel):
    year: int = Field(..., example=2021)
    month: int = Field(..., ge=1, le=12, example=4)

class StartEndDate(BaseModel):
    start: DateInfo = Field(..., description="재직 시작 연월")
    end: Optional[DateInfo] = Field(None, description="재직 종료 연월 (재직 중인 경우 생략)")

class Position(BaseModel):
    title: str = Field(..., example="Tech Lead - Clova X")
    companyName: str = Field(..., example="네이버")
    description: Optional[str] = Field(None, example="클로바X 개발 리드...")
    startEndDate: StartEndDate = Field(..., description="재직 기간 정보")

class DetailedTalentInput(BaseModel):
    positions: List[Position] = Field(...)
    class Config:
        extra = 'allow'     # skills, summary, firstName 등 기타 필드도 허용
        json_schema_extra = {
            "example": {
                "positions": [
                    {
                        "title": "Tech Lead - Clova X",
                        "companyName": "네이버",
                        "startEndDate": {
                            "start": {"year": 2019, "month": 2},
                            "end": {"year": 2021, "month": 4}
                        }
                    }
                ],
                "skills": ["Java","Python"],  # extra=allow 덕분에 허용
                "firstName": "Kim",
                "lastName": "Chulsoo"
            }
        }

class TagResponse(BaseModel):
    tags: List[str]
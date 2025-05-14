# app/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Any

class DateInfo(BaseModel):
    year: int
    month: int

class StartEndDate(BaseModel):
    start: DateInfo
    end: Optional[DateInfo] = None

class Position(BaseModel):
    title: str
    companyName: str
    description: Optional[str]
    startEndDate: StartEndDate

class DetailedTalentInput(BaseModel):
    # 최소한 positions 만 선언, 나머지는 자유롭게 허용
    positions: List[Position]

    class Config:
        extra = 'allow'     # skills, summary, firstName 등 기타 필드도 허용

class TagResponse(BaseModel):
    tags: List[str]


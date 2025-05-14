# app/schemas.py
from pydantic import BaseModel
from typing import List

class TalentInput(BaseModel):
    company: List[str]
    period: List[str]
    title:  List[str]

class TagResponse(BaseModel):
    tags: List[str]


# app/services/inference.py

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List
from app.schemas import TalentInput, TagResponse
from .vector_search import VectorSearch, Document

load_dotenv()
client = OpenAI()
vsearch = VectorSearch()

class InferenceService:
    def __init__(self, llm_client=None, vector_search=None):
        self.client = llm_client or client
        self.vsearch = vector_search or vsearch

    def run(self, payload: TalentInput) -> TagResponse:
        # 1) 벡터 검색: 모든 company에 대해 top_k 문서 수집
        docs: List[Document] = []
        for comp in payload.company:
            docs += self.vsearch.most_similar(comp, top_k=3)

        # 2) Prompt 구성 (다중 경력 지원)
        prompt = (
            "You are an expert recruiter. Given the candidate's career history, "
            "infer their key experiences and skills. Return JSON: { \"tags\": [ ... ] }\n\n"
            "Career History:\n"
        )
        for c, p, t in zip(payload.company, payload.period, payload.title):
            prompt += f"- Company: {c}, Period: {p}, Title: {t}\n"

        prompt += "\nRelated Documents:\n"
        for d in docs:
            snippet = d.content.replace("\n", " ")[:200]
            prompt += f"- [{d.doc_type}] {d.company_name}: {snippet}...\n"

        prompt += (
            "\nAnswer format:\n```json\n{ \"tags\": [\"tag1\", \"tag2\", ...] }\n```"
        )

        # 3) LLM 호출
        resp = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = resp.choices[0].message.content.strip()

        # 코드 블록 제거: LLM이 ```json ... ``` 형태로 감싸서 보낼 수 있음
        if content.startswith("```"):
            lines = content.splitlines()
            # 첫 번째 라인이 ```json 또는 ``` 이면 제거
            if lines[0].startswith("```"):
                lines = lines[1:]
            # 마지막 라인이 ``` 이면 제거
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        # 4) JSON 파싱 & 반환
        parsed = json.loads(content)
        return TagResponse(tags=parsed.get("tags", []))


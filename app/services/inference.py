# app/services/inference.py
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List
from app.schemas import DetailedTalentInput, TagResponse
from .vector_search import VectorSearch, Document

load_dotenv()
client = OpenAI()
vsearch = VectorSearch()

class InferenceService:
    def __init__(self, llm_client=None, vector_search=None):
        self.client = llm_client or client
        self.vsearch = vector_search or vsearch

    def run(self, payload: DetailedTalentInput) -> TagResponse:
        # 1) company 리스트, period 리스트, title 리스트 추출
        companies, periods, titles = [], [], []
        for pos in payload.positions:
            companies.append(pos.companyName)
            # 기간 문자열 포맷
            s = pos.startEndDate.start
            p_str = f"{s.year}.{s.month:02d}"
            if pos.startEndDate.end:
                e = pos.startEndDate.end
                p_str += f"–{e.year}.{e.month:02d}"
            periods.append(p_str)
            titles.append(pos.title)

        # 2) 벡터 검색: 회사별 top 3 문서
        docs: List[Document] = []
        for comp in companies:
            docs += self.vsearch.most_similar(comp, top_k=3)

        # 3) 프롬프트 구성 (한국어)
        prompt = (
            "당신은 전문 리쿠르터입니다.\n"
            "아래 지원자의 상세 이력서를 참고하여, 지원자가 어떤 경험을 했고 어떤 역량을 보유했는지 추론해주세요.\n"
            "추가 또는 변동된 데이터에 대해서는 객관적인 사실(출처 등)을 포함해 작성해 주세요.\n\n"
            "지원자 이력서(JSON):\n"
            f"{json.dumps(payload.dict(), ensure_ascii=False)}\n\n"
            "관련 회사 문서(프로필 및 뉴스):\n"
        )
        for d in docs:
            snippet = d.content.replace("\n", " ")[:200]
            prompt += f"- [{d.doc_type}] {d.company_name}: {snippet}...\n"

        prompt += (
            "\n답변 형식(한국어 JSON):\n```json\n"
            '{ "tags": ["태그1", "태그2", ...] }\n```'
        )

        # 4) LLM 호출
        resp = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = resp.choices[0].message.content.strip()

        # 5) 코드블록 제거
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            content = "\n".join(lines).strip()

        # 6) JSON 파싱
        parsed = json.loads(content)
        return TagResponse(tags=parsed.get("tags", []))


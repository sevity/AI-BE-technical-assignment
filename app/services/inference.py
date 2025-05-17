import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List
from app.schemas import DetailedTalentInput, TagResponse
from .vector_search import VectorSearch, Document

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
client = OpenAI()
vsearch = VectorSearch()

# 서비스명 → 법인명 매핑 테이블
SERVICE_TO_COMPANY_MAP = {
    "토스": "비바리퍼블리카",
    "요기요": "위대한상상",
    "카카오페이": "카카오페이",
    # 필요 시 추가
}

class InferenceService:
    def __init__(self, llm_client=None, vector_search=None):
        self.client = llm_client or client
        self.vsearch = vector_search or vsearch

    def run(self, payload: DetailedTalentInput) -> TagResponse:
        # 1) 회사, 기간, 직무 정보 추출
        companies, periods, titles = [], [], []
        for pos in payload.positions:
            # 매핑 적용
            mapped_name = SERVICE_TO_COMPANY_MAP.get(pos.companyName, pos.companyName)
            logging.debug(f"원본 companyName: {pos.companyName} -> 매핑된 회사명: {mapped_name}")
            companies.append(mapped_name)

            # 기간 문자열 생성
            s = pos.startEndDate.start
            p_str = f"{s.year}.{s.month:02d}"
            if pos.startEndDate.end:
                e = pos.startEndDate.end
                p_str += f"–{e.year}.{e.month:02d}"
            logging.debug(f"parsed period: {p_str}")

            # 직무 로깅
            logging.debug(f"parsed title: {pos.title}")
            periods.append(p_str)
            titles.append(pos.title)

        # 2) 벡터 검색: 회사별 상위 3개 문서 추출
        docs: List[Document] = []
        for comp in companies:
            docs += self.vsearch.most_similar(comp, top_k=3)

        # 3) Few-shot 예시 추가
        example_section = (
            "추론 예시:\n"
            "- Input: talent_ex1.json\n"
            "  Output: 상위권대학교 (연세대학교), 성장기스타트업 경험 (토스 16년–19년 조직·투자 규모 2배 성장), 리더쉽 (챕터 리드·테크 리드), 대용량데이터처리경험 (LLM 대규모 파이프라인 구축)\n"
            "- Input: talent_ex2.json\n"
            "  Output: 상위권대학교 (서울대학교), 대규모 회사 경험 (KT 전략기획실·미디어 성장전략), 리더쉽 (팀장·CFO), IPO 경험 (밀리의서재 IPO), M&A 경험 (밀리의서재 인수)\n"
            "- Input: talent_ex3.json\n"
            "  Output: 상위권대학교 (연세대학교), 대규모 회사 경험 (삼성전자·SKT), M&A 경험 (요기요 사모펀드 매각), 리더쉽 (CPO·창업), 신규 투자유치 (Kasa·LBox)\n"
            "- Input: talent_ex4.json\n"
            "  Output: 상위권대학교 (서울대학교), 대규모 회사 경험 (삼성전자·네이버), 성장기스타트업 경험 (토스 조직 4.5배 확장), 리더쉽 (CTO·Director·팀장), 대용량데이터처리경험 (네이버 하이퍼클로바 개발), M&A 경험 (요기요 매각), 신규 투자유치 (토스 시리즈 F·엘박스 시리즈 B)\n\n"
        )

        # 4) 프롬프트 구성: 연도 기반 성장·프로젝트 정보 반드시 포함하도록 지시
        prompt = (
            "당신은 전문 리쿠르터입니다.\n"
            "지원자의 이력서와 회사 문서 데이터를 참고하여, "
            "포지션 시작-종료 연도 기반 투자 규모 성장, 조직 규모 성장 정보와 "
            "해당 연도에 진행된 주요 프로젝트(예: 하이퍼클로바) 정보를 반드시 태그에 포함해주세요.\n"
            "출력은 예시와 같이 간결한 태그 형태로 작성해주세요.\n\n"
        )
        prompt += example_section
        prompt += (
            "지원자 이력서(JSON):\n"
            f"{json.dumps(payload.dict(), ensure_ascii=False)}\n\n"
            "관련 회사 문서:\n"
        )
        for d in docs:
            snippet = d.content.replace("\n", " ")[:200]
            prompt += f"- [{d.doc_type}] {d.company_name}: {snippet}...\n"
        prompt += (
            "\n답변 형식(한국어 JSON):\n```json\n"
            '{ "tags": ["태그1", "태그2", ...] }\n```'
        )

        # 5) LLM 호출
        resp = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = resp.choices[0].message.content.strip()

        # 6) 코드블록 제거 및 JSON 파싱
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        parsed = json.loads(content)
        return TagResponse(tags=parsed.get("tags", []))

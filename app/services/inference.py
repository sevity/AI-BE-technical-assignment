# app/services/inference.py

import json
import re
import datetime
import calendar
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

# -------------------------------
# 법인명 → 서비스명 유사어(별칭) 목록
# -------------------------------
COMPANY_TO_SERVICE_ALIASES = {
    "비바리퍼블리카": ["토스", "toss", "viva republica"],
    "위대한상상": ["요기요", "yogiyo"],
    "서치라이트": ["searchright ai", "searchright"],
    "KT뮤직": ["genie music", "kt music"],
    "국민은행": ["kookmin bank"],
    "코인텍": ["kointech"],
    "카사": ["kasa"],
    "SK텔레콤": ["sk telecom"],
    "SK플레닛": ["sk planet"],
    "앤틀러": ["antler"],
    "엘박스": ["엘박스"],
    "삼성전자": ["samsung electronics"],
    # 필요 시 추가
}

def normalize(text: str) -> str:
    t = text.lower()
    return re.sub(r'[^a-z0-9ㄱ-힣]+', ' ', t).strip()

def map_service_to_company(service_name: str) -> str:
    norm = normalize(service_name)
    for corp, aliases in COMPANY_TO_SERVICE_ALIASES.items():
        for alias in aliases:
            if alias in norm:
                return corp
    return service_name

class InferenceService:
    def __init__(self, llm_client=None, vector_search=None):
        self.client = llm_client or client
        self.vsearch = vector_search or vsearch

    def run(self, payload: DetailedTalentInput) -> TagResponse:
        # 1) 포지션별 회사명, 기간, 직무 정보 추출 및 로깅
        for pos in payload.positions:
            mapped_name = map_service_to_company(pos.companyName)
            logging.debug(f"원본 companyName: {pos.companyName} -> 매핑된 회사명: {mapped_name}")

            s = pos.startEndDate.start
            p_str = f"{s.year}.{s.month:02d}"
            if pos.startEndDate.end:
                e = pos.startEndDate.end
                p_str += f"–{e.year}.{e.month:02d}"
            logging.debug(f"parsed period: {p_str}")
            logging.debug(f"parsed title: {pos.title}")

        # 2) 벡터 검색: 포지션별 재직 기간을 반영하여 상위 3개 문서 추출
        docs: List[Document] = []
        for pos in payload.positions:
            comp = map_service_to_company(pos.companyName)

            # 시작일
            s = pos.startEndDate.start
            start_date = datetime.date(s.year, s.month, 1)
            # 종료일 (없으면 오늘)
            if pos.startEndDate.end:
                e = pos.startEndDate.end
                last_day = calendar.monthrange(e.year, e.month)[1]
                end_date = datetime.date(e.year, e.month, last_day)
            else:
                end_date = datetime.date.today()

            logging.debug(f"Searching docs for {comp} from {start_date} to {end_date}")
            docs += self.vsearch.most_similar(
                comp,
                start_date=start_date,
                end_date=end_date,
                top_k=3,
            )
        # 3) Few-shot 예시 추가
        example_section = (
            "추론 예시:\n"
            "- Input: talent1.json\n"
            "  Output: 상위권대학교 (KAIST), 대규모 회사 경험 (삼성전자·네이버), 성장기스타트업 경험 (토스 조직 4.5배 확장), 리더쉽 (CTO·Director·팀장), 대용량데이터처리경험 (네이버 하이퍼클로바 개발), M&A 경험 (요기요 매각), 신규 투자유치 (토스 시리즈 F·엘박스 시리즈 B)\n"
            "- Input: talent2.json\n"
            "  Output: 상위권대학교 (고려대학교), 성장기스타트업 경험 (토스 16년–19년 조직·투자 규모 2배 성장), 리더쉽 (챕터 리드·테크 리드), 대용량데이터처리경험 (LLM 대규모 파이프라인 구축)\n"
            "- Input: talent3.json\n"
            "  Output: 상위권대학교 (연세대학교), 대규모 회사 경험 (KT 전략기획실·미디어 성장전략), 리더쉽 (팀장·CFO), IPO 경험 (밀리의서재 IPO), M&A 경험 (밀리의서재 인수)\n"
            "- Input: talent4.json\n"
            "  Output: 상위권대학교 (서울대학교), 대규모 회사 경험 (삼성전자·SKT), M&A 경험 (요기요 사모펀드 매각), 리더쉽 (CPO·창업), 신규 투자유치\n\n"
        )

        PROMPT_TEMPLATE = """\
당신은 전문 리쿠르터입니다. 지원자의 이력서(JSON)와 
"[news] KT (2017-12-21): [2017 디지털혁신상품] KT 기가지니  https://m.ddaily.co.kr/page/view/2017122115161782509"
"[news] 엘박스 (2024-01-26): [더벨][VC 투자기업] 판례 검색 1위 엘박스, 소송금융 시장 뛰어든다  https://www.thebell.co.kr/free/content/ArticleView.asp?key=202401231844596240101829"
형태로 제공되는 뉴스데이터를 참고하여, **아래 7가지 핵심 카테고리**를 가능하다면 포함해주세요.
이 외에도 자유롭게 의미 있는 추가 태그를 뽑아 **태그 형태**로 추출하세요.

뉴스데이터는 반드시 함께 제공되는 링크를 방문하여 본문의 내용을 결과에 반영하세요.
**절대** 이력서에 없는 회사의 문서를 사용하거나, 다른 회사 경험을 만들어내지 마세요.
또한, 예제나 플레이스홀더를 그대로 복붙하지 마세요.

핵심 카테고리:
1. **학력**: 최상위권 대학교 졸업 여부  
예시: “상위권대학교 (학교명)”

2. **대규모 회사 경험**: 메이저 기업 근무 여부  
예시: “대규모 회사 경험 (회사1·회사2·…)”

3. **성장기 스타트업 경험**: 포지션 기간 기반 조직·투자 규모 성장  
예시: “성장기스타트업 경험 (스타트업명 YYYY–YYYY: 조직·투자 규모 X배 성장)”

4. **리더십**: 매니징 직책 보유 여부  
예시: “리더쉽 (직책1·직책2·…)”

5. **대용량 데이터 처리 경험**: 대규모 기술 프로젝트 참여  
예시: “대용량데이터처리경험 (회사명 프로젝트명)”

6. **M&A 경험**: 인수·합병 참여 여부  
예시: “M&A 경험 (인수 대상·매각 대상)”

7. **IPO 및 투자 유치**: 상장·펀딩 주도 여부  
예시: “IPO 경험 (회사명 IPO)” 또는 “신규 투자 유치 경험 (스타트업명 YYYY: 투자액)”

출력은 **JSON** 형태로, `"tags"` 배열에 각 태그를 넣어주세요.  

예시)
```json
{
"tags": [
    "상위권대학교 (연세대학교)",
    "대규모 회사 경험 (네이버·토스)",
    "성장기스타트업 경험 (토스 2016–2019: 조직·투자 규모 2배 성장)",
    "리더쉽 (Tech Lead·Chapter Lead)",
    "대용량데이터처리경험 (네이버 하이퍼클로바 개발)",
    "M&A 경험 (요기요 매각)",
    "신규 투자 유치 경험 (비바리퍼블리카 2018-12-10: 900억 투자)",
    "수상 경력 (사내 우수 엔지니어상 수상)"
]
}
"""

        # 4) 프롬프트 구성
        prompt = PROMPT_TEMPLATE
        prompt += example_section
        prompt += (
            "지원자 이력서(JSON):\n"
            f"{json.dumps(payload.dict(), ensure_ascii=False)}\n\n"
            "관련 회사 문서:\n"
        )
        for d in docs:
            snippet = d.content.replace("\n", " ")[:200]
            prompt += f"- [{d.doc_type}] {d.company_name} ({d.published_at}): {snippet}...\n"
        prompt += (
            "\n답변 형식(한국어 JSON):\n```json\n"
            '{ "tags": ["태그1", "태그2", ...] }\n```'
        )

        # 5) LLM 호출 및 raw 응답 로깅
        resp = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        raw = resp.choices[0].message.content
        logging.debug(f"[LLM RAW RESPONSE]\n{raw!r}")
        content = raw.strip()

        # 6) 코드블록 제거
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        # 7) JSON 파싱 및 에러 로깅
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logging.error("[JSON PARSE ERROR] 응답 내용이 JSON이 아닙니다:\n%s", content, exc_info=True)
            raise

        return TagResponse(tags=parsed.get("tags", []))

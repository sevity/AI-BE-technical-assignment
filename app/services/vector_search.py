# app/services/vector_search.py

import os
import datetime
import psycopg
import logging
from typing import List, NamedTuple, Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# 로거 설정
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class Document(NamedTuple):
    company_name: str
    doc_type: str
    content: str
    published_at: datetime.date


class VectorSearch:
    def __init__(self):
        # PostgreSQL 연결
        logger.debug("Connecting to database: %s", DB_URL)
        self.conn = psycopg.connect(DB_URL, autocommit=True)
        logger.debug("Database connection established")

    def most_similar(
        self,
        company_name: str,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        top_k: int = 5,
    ) -> List[Document]:
        """
        company_name 으로 프로파일 임베딩을 가져와서,
        모든 문서 중 유사도 순으로 정렬하되,
        start_date, end_date 가 주어지면 published_at 으로 필터링 합니다.
        """
        logger.debug(
            "most_similar called with company_name=%r, start_date=%r, end_date=%r, top_k=%d",
            company_name, start_date, end_date, top_k
        )

        with self.conn.cursor() as cur:
            # 1) 회사 프로파일 임베딩 조회
            logger.debug("Fetching profile embedding for %r", company_name)
            cur.execute(
                """
                SELECT embedding
                  FROM company_docs
                 WHERE doc_type = 'profile'
                   AND company_name = %s
                 LIMIT 1
                """,
                (company_name,),
            )
            row = cur.fetchone()
            logger.debug("Profile embedding row: %r", row)
            if not row or row[0] is None:
                logger.error("No embedding found for company %r", company_name)
                raise ValueError(f"No embedding for company {company_name}")
            emb = row[0]

            # 2) 유사 문서 검색 + 기간 필터링
            query = """
                 SELECT company_name, doc_type, content, published_at
                 FROM company_docs
                 WHERE doc_type != 'profile'
                   AND company_name = %s
             """
            params: List = []
            params.append(company_name)


            if start_date is not None and end_date is not None:
                query += " AND published_at BETWEEN %s AND %s"
                params.extend([start_date, end_date])
                logger.debug(
                    "Applying date filter: %s to %s", start_date, end_date
                )

            query += " ORDER BY embedding <=> %s LIMIT %s"
            params.extend([emb, top_k])

            logger.debug("Final SQL query: %s", query.strip())
            logger.debug("Query parameters: %r", params)

            logger.debug("Executing SQL search")
            cur.execute(query, params)
            results = cur.fetchall()
            logger.debug("Fetched %d rows", len(results))

        # NamedTuple 으로 변환
        docs: List[Document] = []
        for company, doc_type, content, published in results:
            logger.debug(
                "Row → company=%r, doc_type=%r, content_len=%d, published_at=%r",
                company, doc_type, len(content), published
            )
            docs.append(Document(
                company_name=company,
                doc_type=doc_type,
                content=content,
                published_at=published,
            ))

        logger.debug("Returning %d Document(s)", len(docs))
        return docs

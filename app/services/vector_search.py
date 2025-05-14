# app/services/vector_search.py
import os
import psycopg
from typing import List, NamedTuple
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

class Document(NamedTuple):
    company_name: str
    doc_type: str
    content: str

class VectorSearch:
    def __init__(self):
        self.conn = psycopg.connect(DB_URL, autocommit=True)

    def most_similar(self, company_name: str, top_k: int = 5) -> List[Document]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT embedding FROM company_docs WHERE doc_type='profile' AND company_name = %s LIMIT 1",
                (company_name,)
            )
            row = cur.fetchone()
            if not row or row[0] is None:
                raise ValueError(f"No embedding for company {company_name}")
            emb = row[0]

            cur.execute(
                """
                SELECT company_name, doc_type, content
                FROM company_docs
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (emb, top_k)
            )
            return [Document(*r) for r in cur.fetchall()]


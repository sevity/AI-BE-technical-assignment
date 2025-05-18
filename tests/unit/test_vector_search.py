# tests/unit/test_vector_search.py

import datetime
import pytest
from app.services.vector_search import VectorSearch, Document

class DummyCursor:
    def __init__(self, rows):
        self._rows = rows
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))

    def fetchone(self):
        # 호출 순서에 따라 프로파일 임베딩, total count, in-range count 반환
        return self._rows.pop(0)

    def fetchall(self):
        # 최종 similarity 결과
        return [("A", "news", "content", datetime.date(2025, 1, 1))]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

class DummyConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

@pytest.fixture
def dummy_db(monkeypatch):
    # 1) fake rows 준비
    rows = [
        ([0.1, 0.2, 0.3],),  # profile embedding
        (10,),               # total non-profile count
        (5,)                 # in-range count
    ]
    cursor = DummyCursor(rows)
    conn = DummyConn(cursor)

    # 2) 환경변수 대체
    monkeypatch.setenv("DATABASE_URL", "dummy")

    # 3) psycopg.connect 모킹 (위치·키워드 인자 모두 허용)
    monkeypatch.setattr("psycopg.connect", lambda *args, **kwargs: conn)

    return cursor

def test_most_similar_filters_and_orders(dummy_db):
    vs = VectorSearch()
    docs = vs.most_similar(
        "AnyCo",
        start_date=datetime.date(2024, 1, 1),
        end_date=datetime.date(2024, 12, 31),
        top_k=1
    )

    # 반환 타입 및 쿼리 구조 검증
    assert isinstance(docs, list)
    assert isinstance(docs[0], Document)

    queries = [q for q, _ in dummy_db.queries]
    assert "BETWEEN %s AND %s" in queries[-2]
    assert "ORDER BY embedding <=> %s LIMIT %s" in queries[-1]

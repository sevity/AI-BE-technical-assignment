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
        # 호출 순서에 따라 다른 값을 반환하도록 간단 구현
        return self._rows.pop(0)
    def fetchall(self):
        # 최종 similarity 결과
        return [("A", "news", "content", datetime.date(2025,1,1))]

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): pass

class DummyConn:
    def __init__(self, cursor):
        self._cursor = cursor
    def cursor(self):
        return self._cursor

@pytest.fixture
def dummy_db(monkeypatch):
    # 첫 fetchone: profile embedding, 두번째 fetchone: total_docs, 이후 fetchone for in_range
    rows = [
        ([0.1, 0.2, 0.3],),  # profile embedding
        (10,),               # total non-profile count
        (5,)                 # in-range count
    ]
    cursor = DummyCursor(rows)
    conn = DummyConn(cursor)
    monkeypatch.setenv("DATABASE_URL", "dummy")
    monkeypatch.setattr("psycopg.connect", lambda *_: conn)
    return cursor

def test_most_similar_filters_and_orders(dummy_db):
    vs = VectorSearch()
    docs = vs.most_similar("AnyCo",
                           start_date=datetime.date(2024,1,1),
                           end_date=datetime.date(2024,12,31),
                           top_k=1)
    # 반환 타입 확인
    assert isinstance(docs, list)
    assert isinstance(docs[0], Document)
    # SQL에 date 필터가 포함되어야 함
    queries = [q for q, _ in dummy_db.queries]
    assert "BETWEEN %s AND %s" in queries[-2]
    assert "ORDER BY embedding <=> %s LIMIT %s" in queries[-1]

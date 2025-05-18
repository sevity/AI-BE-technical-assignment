# tests/unit/test_inference_service.py
import json
import pytest
from types import SimpleNamespace
from app.services.inference_service import InferenceService
from app.schemas import DetailedTalentInput, Position, DateInfo, StartEndDate

@pytest.fixture
def dummy_payload():
    pos = Position(
        title="Engineer",
        companyName="테스트사",
        description=None,
        startEndDate=StartEndDate(
            start=DateInfo(year=2024, month=1),
            end=DateInfo(year=2024, month=6)
        )
    )
    return DetailedTalentInput(positions=[pos])

@pytest.fixture
def fake_docs():
    from app.services.vector_search import Document
    return [Document("테스트사","news","snippet", __import__("datetime").date(2024,1,1))]

@pytest.fixture
def fake_llm(monkeypatch, fake_docs):
    # 1) vector search가 fake_docs 반환
    monkeypatch.setenv("DATABASE_URL", "dummy")
    monkeypatch.setattr("app.deps.get_vector_search", lambda: SimpleNamespace(most_similar=lambda *args, **kw: fake_docs))
    # 2) LLM 클라이언트가 항상 JSON 응답
    real = {"tags": ["태그1","태그2"]}
    fake_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(real)))]
    )
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda *a, **k: fake_resp)))
    monkeypatch.setattr("app.deps.get_openai_client", lambda: fake_client)
    return fake_client

def test_inference_service_parses_tags(dummy_payload, fake_llm):
    svc = InferenceService(llm_client=fake_llm, vector_search=None)
    result = svc.run(dummy_payload)
    assert "tags" in result.dict()
    assert result.tags == ["태그1","태그2"]

def test_inference_service_empty_positions_raises():
    svc = InferenceService()
    with pytest.raises(ValueError):
        svc.run(DetailedTalentInput(positions=[]))

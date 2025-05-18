# tests/unit/test_inference_service.py
import json
import pytest
from types import SimpleNamespace
from app.services.inference import InferenceService
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
def fake_llm(monkeypatch):
    # LLM 클라이언트만 가짜로 교체
    real = {"tags": ["태그1","태그2"]}
    fake_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(real)))]
    )
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda *a, **k: fake_resp)))
    return fake_client

@pytest.fixture
def fake_vs(fake_docs):
    # vector_search.most_similar이 fake_docs를 반환하도록
    return SimpleNamespace(most_similar=lambda *args, **kwargs: fake_docs)

def test_inference_service_parses_tags(dummy_payload, fake_llm, fake_vs):
    svc = InferenceService(llm_client=fake_llm, vector_search=fake_vs)
    result = svc.run(dummy_payload)
    assert result.tags == ["태그1","태그2"]

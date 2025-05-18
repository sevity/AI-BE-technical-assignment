# tests/unit/test_router.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_infer_endpoint_empty_positions():
    resp = client.post("/infer", json={"positions": []})
    assert resp.status_code == 400
    assert "비어있습니다" in resp.json()["detail"]

def test_infer_endpoint_invalid_payload():
    # positions 필드 자체가 없으면 FastAPI validation error
    resp = client.post("/infer", json={})
    assert resp.status_code == 422

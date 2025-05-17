# tests/test_inference.py
import json
import os
import pytest
from types import SimpleNamespace

from fastapi.testclient import TestClient
from app.main import app

# 실제 API 테스트 클라이언트
@pytest.fixture(scope="session")
def client():
    return TestClient(app)

# 테스트용 real_response 파일 로드 유틸리티
def load_real_response(filename: str) -> dict:
    base = os.path.join(os.path.dirname(__file__), "real_response_")
    path = f"{base}{filename}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# 샘플 매핑: talent 파일명 -> real_response 파일명 -> 최소 포함 태그
cases = [
    ("talent_ex1", "ex1", ["상위권대학교", "성장기스타트업 경험", "리더쉽", "대용량데이터처리경험"]),
    ("talent_ex2", "ex2", ["상위권대학교", "대규모 회사 경험", "리더쉽", "IPO", "M&A 경험"]),
    ("talent_ex3", "ex3", ["상위권대학교", "대규모 회사 경험", "M&A 경험", "리더쉽", "신규 투자 유치 경험"]),
    ("talent_ex4", "ex4", ["상위권대학교", "대규모 회사 경험", "M&A 경험", "리더쉽", "신규 투자 유치 경험", "성장기스타트업 경험", "대용량데이터처리경험"]),
]

@pytest.mark.parametrize("talent_file, resp_key, must_include", cases)
def test_infer_tags(client, mocker, talent_file, resp_key, must_include):
    # 1) payload 로드
    payload_path = os.path.join(
        os.path.dirname(__file__),
        "..", "example_datas",
        f"{talent_file}.json"
    )
    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # 2) 캡쳐된 real_response 로 fake_resp 생성 (SimpleNamespace 중첩)
    real_resp = load_real_response(resp_key)
    fake_resp = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(real_resp, ensure_ascii=False)
                )
            )
        ]
    )

    # 3) fake_client 정의 (chat.completions.create 호출 시 fake_resp 반환)
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda *args, **kwargs: fake_resp
            )
        )
    )

    # 4) OpenAI 호출 patch: get_openai_client() 가 fake_client 반환하도록
    mocker.patch(
        "app.deps.get_openai_client",
        return_value=fake_client
    )

    # 5) 엔드포인트 호출 및 검증
    res = client.post("/infer", json=payload)
    assert res.status_code == 200, res.text

    tags = res.json().get("tags", [])
    for expected in must_include:
        assert any(expected in tag for tag in tags), f"Expected '{expected}' in {tags}"

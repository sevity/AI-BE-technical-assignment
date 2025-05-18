# tests/unit/test_utils.py
import pytest
from app.services.inference_service import normalize, map_service_to_company

def test_normalize_removes_special_chars():
    assert normalize("Hello, World!") == "hello world"
    assert normalize("토스 (Toss)_Test!") == "토스 toss test"

def test_map_service_to_company_with_alias():
    # "toss" → "비바리퍼블리카"
    assert map_service_to_company("toss") == "비바리퍼블리카"
    # 대소문자 무관
    assert map_service_to_company("TOSS Korean") == "비바리퍼블리카"

def test_map_service_to_company_no_alias():
    assert map_service_to_company("UnknownCorp") == "UnknownCorp"

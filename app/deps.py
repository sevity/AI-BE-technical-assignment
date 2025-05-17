# app/deps.py
from functools import lru_cache
from openai import OpenAI
from app.services.vector_search import VectorSearch

@lru_cache()
def get_openai_client():
    return OpenAI()

@lru_cache()
def get_vector_search():
    return VectorSearch()


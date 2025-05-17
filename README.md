## AI-BE-Technical-Assignment

이 저장소는 SearcHRight AI 백엔드 기술 과제를 위한 코드베이스입니다.
원본 과제 안내는 `docs/assignment.md`를 참고하세요.

---

## 🚀 프로젝트 목적

* **목표**: 회사·재직기간·타이틀 정보만으로 지원자의 경험/역량을 자동으로 추론해 태그화된 리스트를 반환하는 REST API 구현
* **기술 스택**: FastAPI, PostgreSQL + pgvector, OpenAI GPT, Docker Compose, Nginx, pytest

---

## 📂 주요 디렉터리 구조

```
├── app/                      # FastAPI 애플리케이션 코드
│   ├── main.py               # 엔트리포인트
│   ├── deps.py               # DI(의존성) 설정
│   ├── models.py             # SQLAlchemy ORM 정의
│   ├── schemas.py            # Pydantic 스키마
│   └── services/             # 핵심 로직
│       ├── vector_search.py  # 벡터 검색 로직
│       └── inference.py      # LLM 기반 태그 추론 서비스
├── example_datas/            # 샘플 JSON 및 데이터 세팅 스크립트
│   ├── setup_company_data.py
│   ├── setup_company_news_data.py
│   ├── talent_ex1.json
│   ├── talent_ex2.json
│   ├── talent_ex3.json
│   └── talent_ex4.json
├── scripts/                  # 벡터 임베딩 초기화 스크립트
│   └── embed_docs.py
├── tests/                    # 테스트 코드
│   ├── conftest.py
│   └── test_inference.py
├── nginx/                    # Nginx 리버스 프록시 설정
│   └── default.conf
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md                 # (이 파일)
```

---

## 전체 아키텍처 흐름

```mermaid
flowchart LR
  A[Talent JSON] --> B[FastAPI /infer 엔드포인트]
  B --> C{Vector Search}
  C --> |유사 문서 조회| D[Postgres (pgvector)]
  D --> |docs + embeddings| E[Inference Service]
  E --> |프롬프트 생성| F[OpenAI ChatCompletion]
  F --> |응답| G[TagResponse]
  G --> H[클라이언트 응답]
```

---

## ⚙️ 환경 설정 & 의존성

```bash
# 1. Python 3.13 설치 (pyenv)
pyenv install 3.13.0
pyenv local 3.13.0

# 2. Poetry 설치
curl -sSL https://install.python-poetry.org | python -

# 3. 프로젝트 의존성 설치
poetry install

# 4. 추가 패키지 (FastAPI, OpenAI, pgvector 등)
poetry add fastapi uvicorn openai psycopg[binary] pgvector sqlalchemy pytest pytest-asyncio httpx pytest-mock respx
```

---

## 🐳 Docker Compose 기동

```bash
docker compose up -d --build
```

* **Postgres**: pgvector 확장 포함
* **API**: 9000 포트
* **Nginx**: 8000 → API(9000) 프록시

---

## 🗄️ 데이터베이스 초기화 & DDL

```sql
-- 1) pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2) company_docs 테이블 생성
CREATE TABLE company_docs (
  id SERIAL PRIMARY KEY,
  company_name TEXT,
  doc_type TEXT,
  content TEXT,
  embedding VECTOR(1536)
);

-- 3) 벡터 인덱스 생성
CREATE INDEX idx_company_docs_embedding ON company_docs USING ivfflat (embedding vector_cosine_ops);
```

---

## 📊 예제 데이터 적재

```bash
# 회사 및 뉴스 데이터 세팅
poetry run python example_datas/setup_company_data.py
poetry run python example_datas/setup_company_news_data.py
```

---

## 🚀 서버 실행 & API 테스트

```bash
# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# 샘플 호출
curl -X POST http://localhost:8000/infer \
     -H "Content-Type: application/json" \
     -d @example_datas/talent_ex1.json | jq
```

* Swagger UI: `http://localhost:8000/docs`
* ReDoc:        `http://localhost:8000/redoc`

---

## ✅ 단위 & 통합 테스트

```bash
poetry run pytest -q --disable-warnings --maxfail=1
```

* `tests/test_inference.py` 에서 샘플 3건에 대해 최소 태그(`상위권대학교`, `리더쉽`) 포함 여부 자동 검증
* OpenAI 호출은 `pytest-mock` 또는 `respx` 로 Mocking 처리

---

## 📦 CI/CD & 배포

* `.github/workflows/ci.yml` 에 **테스트** 및 **Docker 빌드** 설정 완료
* `docker-compose.yml` 로 로컬 및 스테이징 배포 지원

---

## 🚧 TODO (향후 개선 사항)

* **ORM 통합**: 현재 `psycopg` 직접 SQL을 사용 중인 `embed_docs.py`와 `vector_search.py`를 SQLAlchemy ORM 매핑으로 전환

  * `app/models.py`에 `CompanyDoc` ORM 클래스 정의
  * `app/db.py` 및 `app/deps.py`에 세션 및 의존성 주입 설정 추가
  * CRUD 로직(`INSERT`, `SELECT`)을 ORM 방식으로 리팩토링
* **모니터링 & 로깅 개선**: 리퀘스트별 처리 시간 측정, Prometheus 메트릭·Grafana 대시보드 통합

---

## 📄 과제 안내

원본 과제 설명, 제출 기한, 토큰 관리 등은 `docs/assignment.md`를 참고하세요.
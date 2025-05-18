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
├── scripts/                  # 초기화 및 임베딩 스크립트
│   ├── init_db.py            # 스키마·인덱스 생성 스크립트
│   └── embed_docs.py         # 벡터 임베딩 삽입 스크립트
├── tests/                    # 테스트 코드
│   ├── unit/                 # **단위 테스트** 디렉터리
│   │   ├── test_utils.py
│   │   ├── test_vector_search.py
│   │   ├── test_inference_service.py
│   │   └── test_router.py
│   └── test_inference.py
│   └── conftest.py           
│   ├── real_response_ex1.json  # LLM 실제 응답 예시
│   ├── real_response_ex2.json
│   ├── real_response_ex3.json
│   └── real_response_ex4.json
├── nginx/                    # Nginx 리버스 프록시 설정
│   └── default.conf
├── Dockerfile                # API 서비스 이미지 정의
├── entrypoint.sh             # 컨테이너 기동 시 자동 실행 스크립트
├── docker-compose.yml        # 전체 서비스 오케스트레이션
├── pyproject.toml
└── README.md                 # (이 파일)
```

---

## 전체 아키텍처 흐름

```mermaid
flowchart LR
  A["Talent JSON 입력"] --> B["FastAPI /infer 엔드포인트"]
  B --> C["Vector Search (Postgres + pgvector)"]
  C --> D["Inference Service (프롬프트 생성)"]
  D --> E["OpenAI ChatCompletion 호출"]
  E --> F["응답 파싱 → TagResponse 생성"]
  F --> G["클라이언트 반환"]
```

---

## 🔧 환경 변수 설정

컨테이너가 실행되기 전에 루트에 `.env` 파일을 만들어주세요:

```bash
cat > .env <<EOF
DATABASE_URL=postgresql://searchright:searchright@postgres:5432/searchright
OPENAI_API_KEY=sk-<your_openai_api_key>
EOF
```

---

## 🚀 초기 구동 방법

**A. 전체 서비스 자동 구동**

```bash
# Docker Compose로 전체 컨테이너 빌드 및 실행
docker compose up --build
```

* 자동 실행 순서:

  1. `scripts/init_db.py` → 스키마·인덱스 생성
  2. `example_datas/setup_company_data.py`, `example_datas/setup_company_news_data.py` → 예제 데이터 삽입
  3. `scripts/embed_docs.py` → 텍스트 → 임베딩 변환 후 `company_docs` 테이블에 삽입
  4. FastAPI 서버 기동 (`uvicorn app.main:app --host 0.0.0.0 --port 9000`)
* Nginx를 통해 `http://localhost:8000`에서 API 호출 가능 (내부 API 서버: 9000 포트)

**B. API 호출 예시**

```bash
curl -X POST http://localhost:9000/infer \
     -H "Content-Type: application/json" \
     -d @example_datas/talent_ex1.json | jq
```

> 🚧 **주의**: 초기 임베딩 단계는 벡터 변환 API 호출이 포함되어 있어 시간이 소요될 수 있습니다. API호출은 새 터미널을 열어서 수행해주세요.

---

## 🚀 API 문서

* Swagger UI: `http://localhost:9000/docs`
* ReDoc:        `http://localhost:9000/redoc`

---

## ✅ 단위 & 통합 테스트

### 1. 테스트 구조

모듈별 단위 테스트(Unit Test)와 엔드포인트 레벨 통합 테스트(Integration Test)를 분리하여 관리합니다.

```
tests/
├── unit/         # 핵심 로직 단위 테스트
│   ├── test_utils.py
│   ├── test_vector_search.py
│   ├── test_inference_service.py
│   └── test_router.py
└── test_inference.py # integration test
└── conftest.py   # 공용 픽스처 및 설정
```

### 2. 테스트 실행 방법
호스트머신에서 다음을 수행해주세요.
```bash
poetry install --with dev
poetry run pytest -q --disable-warnings --maxfail=1
```

* `tests/test_inference.py` 에서 샘플 4개 케이스에 대해 아래 기준으로 태그 포함 여부를 검증합니다.

| 케이스       | 최소 포함 태그                                                                                                                                    |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `talent_ex1` | 상위권대학교, 성장기스타트업 경험, 리더쉽, 대용량데이터처리경험                                                                                        |
| `talent_ex2` | 상위권대학교, 대규모 회사 경험, 리더쉽, IPO, M&A 경험                                                                                                 |
| `talent_ex3` | 상위권대학교, 대규모 회사 경험, M&A 경험, 리더쉽, 신규 투자 유치 경험                                                                                 |
| `talent_ex4` | 상위권대학교, 대규모 회사 경험, M&A 경험, 리더쉽, 신규 투자 유치 경험, 성장기스타트업 경험, 대용량데이터처리경험                                           |

> 🎯 각 케이스별로 위에 제시된 태그가 모두 **포함**되어야 테스트가 성공합니다.

---

## 🚧 TODO (향후 개선 사항)

* **ORM 통합**: 현재 `psycopg` 직접 SQL을 사용 중인 `embed_docs.py`와 `vector_search.py`를 SQLAlchemy ORM 매핑으로 전환
* CI/CD 배포 설정
* pytest-cov 를 도입해 커버리지(coverage) 기준을 설정하고, 최소 80% 이상을 목표
* **모니터링 & 로깅 개선**: Prometheus 메트릭, Grafana 대시보드 통합

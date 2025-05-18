# 1. 베이스 이미지
FROM python:3.13-slim

# 2. 작업 디렉토리
WORKDIR /app

# 3. 의존성 설치
COPY pyproject.toml poetry.lock ./
RUN pip install "poetry>=1.5" && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# 4. 소스 복사
COPY . .

# 5. 포트 노출
EXPOSE 9000

# 6. 실행 커맨드
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]


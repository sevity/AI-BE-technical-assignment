FROM python:3.13-slim

WORKDIR /app

# 1) Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*
# 2) Install Poetry and project dependencies
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev --no-root

# 3) Copy application code and scripts
COPY app/ ./app
COPY scripts/ ./scripts
COPY example_datas/ ./example_datas

# 4) Copy and set up entrypoint
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# 5) Expose application port
EXPOSE 9000

# 6) Default entrypoint to initialize DB, load data, embed docs, then start server
ENTRYPOINT ["./entrypoint.sh"]

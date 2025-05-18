FROM python:3.13-slim

# Ensure Python output is not buffered, so logs appear immediately
ENV PYTHONUNBUFFERED=1

# 1) Set working directory
WORKDIR /app

# 2) Install system dependencies (build tools + pg_isready)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 3) Install Poetry and project dependencies
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev --no-root

# 4) Copy application sources, scripts, and example data
COPY app/ ./app
COPY scripts/ ./scripts
COPY example_datas/ ./example_datas
COPY src/ ./src

# 5) Copy entrypoint and make executable
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# 6) Expose application port
EXPOSE 9000

# 7) Use entrypoint to wait for DB, initialize, load, embed, and launch server
ENTRYPOINT ["./entrypoint.sh"]
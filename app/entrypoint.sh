#!/usr/bin/env sh
set -e

echo "▶️ Waiting for PostgreSQL to be ready..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" >/dev/null 2>&1; do
  printf "."
  sleep 1
done
echo "\n✅ PostgreSQL is up!"

echo "▶️ Initializing database schema and indexes..."
python scripts/init_db.py

echo "▶️ Loading example data..."
python example_datas/setup_company_data.py
python example_datas/setup_company_news_data.py

echo "▶️ Embedding documents..."
python scripts/embed_docs.py

echo "▶️ Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 9000

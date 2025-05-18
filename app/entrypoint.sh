#!/usr/bin/env sh
set -e

echo "▶️ Initializing database schema and indexes..."
python scripts/init_db.py

echo "▶️ Loading example data..."
python example_datas/setup_company_data.py
python example_datas/setup_company_news_data.py

echo "▶️ Embedding documents..."
python scripts/embed_docs.py

echo "▶️ Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 9000

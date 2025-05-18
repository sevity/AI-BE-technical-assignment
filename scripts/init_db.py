# scripts/init_db.py
import os
import psycopg
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the database connection URL
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL is not set")

print(f"Connecting to database: {db_url}")

# Establish a connection to PostgreSQL with autocommit enabled
with psycopg.connect(db_url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("""
        -- 1) Enable the pgvector extension if not already present
        CREATE EXTENSION IF NOT EXISTS vector;

        -- 2) Create the 'company' table
        CREATE TABLE IF NOT EXISTS company (
          id   SERIAL PRIMARY KEY,
          name VARCHAR(255)   NOT NULL,
          data JSONB          NOT NULL
        );

        -- 3) Create the 'company_news' table with a foreign key to 'company'
        CREATE TABLE IF NOT EXISTS company_news (
          id            SERIAL PRIMARY KEY,
          company_id    INTEGER NOT NULL
                         REFERENCES company(id) ON DELETE CASCADE,
          title         VARCHAR(1000) NOT NULL,
          original_link TEXT,
          news_date     DATE        NOT NULL
        );

        -- 4) Create the 'company_docs' table
        CREATE TABLE IF NOT EXISTS company_docs (
          id           SERIAL PRIMARY KEY,
          company_name TEXT                  NOT NULL,
          doc_type     TEXT                  NOT NULL,
          content      TEXT                  NOT NULL,
          embedding    VECTOR(1536),
          content_hash TEXT GENERATED ALWAYS AS (md5(content)) STORED,
          published_at DATE
        );

        -- 5) Create an index on the embedding column for vector similarity search
        CREATE INDEX IF NOT EXISTS idx_company_docs_embedding
          ON company_docs USING ivfflat (embedding vector_cosine_ops);

        -- 6) Ensure uniqueness of (company_name, doc_type, content_hash)
        CREATE UNIQUE INDEX IF NOT EXISTS idx_company_docs_news_full
          ON company_docs (company_name, doc_type, content_hash);
        """)
        print("Schema and indexes have been successfully created or verified.")
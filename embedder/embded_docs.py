import os
import json
import psycopg
import tiktoken
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

db_url = os.getenv("DATABASE_URL")
client = OpenAI()

# Connect to Postgres
conn = psycopg.connect(db_url, autocommit=True)

# Tokenizer setup for embedding chunking
enc = tiktoken.get_encoding("cl100k_base")
MAX_TOKENS = 8000

def chunk_text(text, max_tokens=MAX_TOKENS):
    """
    Split text into chunks not exceeding max_tokens tokens each.
    """
    tokens = enc.encode(text)
    for i in range(0, len(tokens), max_tokens):
        yield enc.decode(tokens[i : i + max_tokens])

# Prepare a mapping from company_id to company_name
with conn.cursor() as cur:
    cur.execute("SELECT id, name FROM company;")
    company_map = {row[0]: row[1] for row in cur.fetchall()}

# Main insertion loop
with conn.cursor() as cur:
    # Optional: clear existing embeddings
    # cur.execute("DELETE FROM company_docs;")

    # 1) Process company profiles
    cur.execute("SELECT name, data FROM company;")
    for name, data in cur.fetchall():
        content = json.dumps(data, ensure_ascii=False)
        chunks = list(chunk_text(content))
        embeddings = []
        for chunk in chunks:
            resp = client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002"
            )
            embeddings.append(resp.data[0].embedding)
        # Compute element-wise average of chunk embeddings
        avg_emb = [sum(vals) / len(vals) for vals in zip(*embeddings)]
        # Insert with ON CONFLICT DO NOTHING
        cur.execute(
            """
            INSERT INTO company_docs (company_name, doc_type, content, embedding)
            VALUES (%s, 'profile', %s, %s)
            ON CONFLICT (company_name, doc_type) DO NOTHING;
            """,
            (name, content, avg_emb)
        )
        if cur.rowcount:
            logger.info(f"Inserted profile embedding for {name}")
        else:
            logger.info(f"Skipped existing profile embedding for {name}")

    # 2) Process company news (use title and link)
    cur.execute("""
        SELECT n.company_id, n.title, n.original_link
        FROM company_news n
        JOIN company c ON n.company_id = c.id;
    """)
    for comp_id, title, link in cur.fetchall():
        company_name = company_map.get(comp_id, "Unknown")
        text = f"{title}\n\n{link}"
        chunks = list(chunk_text(text))
        embeddings = []
        for chunk in chunks:
            resp = client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002"
            )
            embeddings.append(resp.data[0].embedding)
        avg_emb = [sum(vals) / len(vals) for vals in zip(*embeddings)]
        # Insert with ON CONFLICT DO NOTHING
        cur.execute(
            """
            INSERT INTO company_docs (company_name, doc_type, content, embedding)
            VALUES (%s, 'news', %s, %s)
            ON CONFLICT (company_name, doc_type, content) DO NOTHING;
            """,
            (company_name, text, avg_emb)
        )
        if cur.rowcount:
            logger.info(f"Inserted news embedding for {company_name}")
        else:
            logger.info(f"Skipped existing news embedding for {company_name}")

logger.info("✅ Embedding insertion complete")

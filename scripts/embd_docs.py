import os
import json
import psycopg
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv
import hashlib  # for computing content_hash
from datetime import date

# Load environment variables
load_dotenv()

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

with conn.cursor() as cur:
    # Prepare a mapping from company_id to company_name
    cur.execute("SELECT id, name FROM company;")
    company_map = {row[0]: row[1] for row in cur.fetchall()}

    # 1) Process only unembedded company profiles
    cur.execute("SELECT name, data FROM company;")
    for name, data in cur.fetchall():
        # Skip if profile embedding already exists
        cur.execute(
            """
            SELECT 1
              FROM company_docs
             WHERE company_name = %s
               AND doc_type     = 'profile'
            """,
            (name,)
        )
        if cur.fetchone():
            continue

        content = json.dumps(data, ensure_ascii=False)
        chunks = list(chunk_text(content))
        embeddings = []
        for chunk in chunks:
            resp = client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002"
            )
            embeddings.append(resp.data[0].embedding)
        avg_emb = [sum(vals) / len(vals) for vals in zip(*embeddings)]

        cur.execute(
            """
            INSERT INTO company_docs (company_name, doc_type, content, embedding)
            VALUES (%s, 'profile', %s, %s)
            """,
            (name, content, avg_emb)
        )
        print(f"Profile → {name} ({len(chunks)} chunk(s))")

    # 2) Process only unembedded company news, now pulling news_date too
    cur.execute(
        """
        SELECT cn.company_id
             , cn.title
             , cn.original_link
             , cn.news_date      -- ← 추가
        FROM company_news cn
        JOIN company c
          ON c.id = cn.company_id
        LEFT JOIN company_docs cd
          ON cd.company_name = c.name
         AND cd.doc_type     = 'news'
         AND cd.content_hash = md5(cn.title || '\n\n' || cn.original_link)
        WHERE cd.company_name IS NULL
        """
    )
    for comp_id, title, link, news_date in cur.fetchall():
        company_name = company_map.get(comp_id, "Unknown")
        text = f"{title}\n\n{link}"

        # Compute content_hash the same way as table does
        content_hash = hashlib.md5(text.encode('utf-8')).hexdigest()

        chunks = list(chunk_text(text))
        embeddings = []
        for chunk in chunks:
            resp = client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002"
            )
            embeddings.append(resp.data[0].embedding)
        avg_emb = [sum(vals) / len(vals) for vals in zip(*embeddings)]

        cur.execute(
            """
            INSERT INTO company_docs
              (company_name, doc_type, content, embedding, published_at)
            VALUES
              (%s, 'news', %s, %s, %s)     -- ← published_at 추가
            ON CONFLICT (company_name, doc_type, content_hash) DO NOTHING;
            """,
            (company_name, text, avg_emb, news_date)
        )
        print(f"News → {company_name} ({len(chunks)} chunk(s))")

print("✅ Embedding insertion complete")

from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# The .env file is in the project root, two folders up from this script
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise SystemExit("DATABASE_URL was not found. Check your root .env file.")

engine = create_engine(database_url)

with engine.connect() as connection:
    version = connection.execute(text("SELECT version();")).scalar()
    vector = connection.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
    ).scalar()

print("Connected successfully!")
print("PostgreSQL:", version)
print("pgvector version:", vector or "NOT ENABLED")
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# One engine for the whole application. It manages a pool of connections.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# A factory that creates new database sessions.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# Every database model will inherit from this class.
class Base(DeclarativeBase):
    pass


# FastAPI dependency: one session per request, always closed afterward.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
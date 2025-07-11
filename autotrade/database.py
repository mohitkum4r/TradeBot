from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from .config import Config

engine = create_engine(
    Config.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True for debugging SQL statements
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Provides a transactional scope around a series of operations.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

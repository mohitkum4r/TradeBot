# infrastructure/database/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import Config

engine = create_engine(
    Config.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
database.py — SQLAlchemy engine, session factory ve tablo oluşturma.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./local_eokul.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI Depends ile kullanılacak DB oturumu üreteci."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Uygulama başlangıcında tabloları oluştur (idempotent)."""
    from app.models import Class, Student, Grade  # noqa: F401 — import triggers metadata
    Base.metadata.create_all(bind=engine)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from databases import Database
import os

# At the top of database.py
from dotenv import load_dotenv
load_dotenv()  # This loads the variables from .env

#DATABASE_URL = "postgresql://aditya:aditya123@localhost:5432/cricket_db"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aditya:aditya123@localhost:5432/cricket_db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Connecting to database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "2"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "1"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "false").lower() in {"1", "true", "yes"}
# Per-statement ceiling in ms; 0/unset = none. Only the web dyno sets it (Procfile): Heroku's
# router abandons a request at 30 s, but a runaway query would otherwise keep its pool slot
# while every other request queues behind it. Batch jobs share this engine and must not get it.
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "0") or 0)

print(
    "DB pool config:",
    f"pool_size={DB_POOL_SIZE}",
    f"max_overflow={DB_MAX_OVERFLOW}",
    f"pool_timeout={DB_POOL_TIMEOUT}",
    f"pool_recycle={DB_POOL_RECYCLE}",
    f"statement_timeout_ms={DB_STATEMENT_TIMEOUT_MS or 'none'}",
)

_connect_args = (
    {"options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}"} if DB_STATEMENT_TIMEOUT_MS > 0 else {}
)

database = Database(DATABASE_URL)
engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database():
    # Optional safety for local/dev only; production should rely on migrations.
    if AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)

def get_database_connection():
    return engine, SessionLocal

def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

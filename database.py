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

database = Database(DATABASE_URL)
engine = create_engine(
    DATABASE_URL,
    pool_size=3,  # Base connections per worker (4 workers * 3 = 12 base)
    max_overflow=5,  # Overflow per worker (4 workers * 5 = 20 overflow, 32 total max)
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)

def get_database_connection():
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal

def get_session():
    _, SessionLocal = get_database_connection()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
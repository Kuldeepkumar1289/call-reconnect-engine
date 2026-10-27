from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

database_engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True, 
    pool_recycle=3600    
)

DatabaseSessionLocal = sessionmaker(
    autocommit=False,   
    autoflush=False,     
    bind=database_engine
)

BaseModel = declarative_base()


def get_database_session():
    current_session = DatabaseSessionLocal()
    try:
        yield current_session
    finally:
        current_session.close()  
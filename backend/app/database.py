from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(bind=ENGINE)

Base = declarative_base()

def get_db():       # Activates database
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



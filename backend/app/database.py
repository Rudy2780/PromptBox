from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# ``pool_pre_ping`` issues a cheap liveness check before handing out a pooled
# connection. Neon suspends idle compute and drops the underlying sockets, so
# without this the first request after an idle period fails on a dead
# connection instead of transparently reconnecting.
ENGINE = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=ENGINE)

Base = declarative_base()

def get_db():       # Activates database
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



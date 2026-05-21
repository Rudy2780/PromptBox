from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class UserInfo(Base):       # Class for DB how user account will be organized

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable = False)
    created_at = Column(DateTime, default=datetime.utcnow)

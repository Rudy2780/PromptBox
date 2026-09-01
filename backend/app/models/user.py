from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class UserInfo(Base):       # Class for DB how user account will be organized

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    # Nullable: an account created through Google or GitHub has no password to
    # hash. NULL here means "this account cannot be signed into with a
    # password", and the login route treats it exactly that way -- it is not a
    # blank password and it must never verify against one.
    hashed_password = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

from sqlalchemy import Column, Integer, String, Text
from app.database import Base

class Template(Base):
    """A reusable prompt template with placeholder sections"""
    
    __tablename__ = "templates"
    
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    content  = Column(Text, nullable=False)
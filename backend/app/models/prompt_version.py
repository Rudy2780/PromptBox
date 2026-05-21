from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from datetime import datetime

from app.database import Base

class PromptVersion(Base):
    """A saved snapshot of a prompt and its optional LLM response"""
    
    __tablename__ = "prompt_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    tag = Column(String(32), nullable=True)
    prompt_text = Column(Text, nullable=False)
    
    response_text = Column(Text, nullable=True)
    response_model = Column(String(100), nullable=True)
    response_latency = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow) 

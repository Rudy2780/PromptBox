import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./promptbox.db"
    JWT_SECRET = os.getenv("JWT_SECRET") or "dev-secret-change-me"

settings = Settings()

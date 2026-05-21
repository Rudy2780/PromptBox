from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.models import user
from app.models import prompt_version
from app.database import Base, ENGINE
from app.api.router import api_router

Base.metadata.create_all(bind=ENGINE)

def ensure_prompt_versions_tag_column() -> None:
    inspector = inspect(ENGINE)
    columns = {column["name"] for column in inspector.get_columns("prompt_versions")}
    if "tag" not in columns:
        with ENGINE.begin() as conn:
            conn.execute(text("ALTER TABLE prompt_versions ADD COLUMN tag VARCHAR(32)"))

ensure_prompt_versions_tag_column()

app = FastAPI(title="PromptBox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://prompt-box-seven.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
def root():
    return {"status": "PromptBox backend running"}

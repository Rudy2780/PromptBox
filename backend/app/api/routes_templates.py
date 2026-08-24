from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi import Depends
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.template import Template

router = APIRouter(prefix="/api/templates", tags=["templates"])

class TemplateResponse(BaseModel):
    id: int
    name: str
    category: str
    content: str

    # Was declared at module scope, where it configured nothing -- it has to be
    # a class attribute to apply to the model.
    model_config = {"from_attributes": True}

@router.get("/", response_model=List[TemplateResponse])
def get_templates(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> List[TemplateResponse]:
    query = db.query(Template)
    if category:
        query = query.filter(Template.category == category)
    return query.all()

@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db)
) -> TemplateResponse:
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
from fastapi import APIRouter

from .routes_health import router as health_router
from .routes_validate_key import router as validate_key_router
from .routes_execute import router as execute_router
from .routes_auth import router as auth_router
from .routes_versions import router as versions_router
from .routes_export import router as export_router
from .routes_templates import router as templates_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health")
api_router.include_router(validate_key_router, prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(execute_router)
api_router.include_router(versions_router)
api_router.include_router(export_router)
api_router.include_router(templates_router)
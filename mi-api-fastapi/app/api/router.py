from fastapi import APIRouter
from app.api.routes import health, auth, worker, manager, admin
api_router=APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(worker.router)
api_router.include_router(manager.router)
api_router.include_router(admin.router)

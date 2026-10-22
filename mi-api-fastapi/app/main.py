from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.db.session import Base, engine
from app import models  # noqa: F401
from app.seed import seed_demo
from app.core.middleware import SecurityHeadersMiddleware, LoginRateLimitMiddleware, CSRFMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.seed_demo_data:
        seed_demo()
    yield

app=FastAPI(title=settings.app_name,version="1.0.0",lifespan=lifespan)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoginRateLimitMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin],allow_credentials=True,allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"],allow_headers=["Content-Type","X-CSRF-Token"])
app.include_router(api_router,prefix=settings.api_prefix)
@app.get("/")
def root(): return {"status":"ok","app":settings.app_name,"variant":settings.arch_variant,"docs":"/docs"}

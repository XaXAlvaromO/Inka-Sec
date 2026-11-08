import secrets, time
from collections import deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings
from app.core.dependencies import client_ip

LOGIN_PATH = f"{settings.api_prefix}/auth/login"
VERIFY_2FA_PATH = f"{settings.api_prefix}/auth/2fa/verify"
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["X-Frame-Options"]="DENY"
        response.headers["Referrer-Policy"]="no-referrer"
        response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"]="same-origin"
        if not request.url.path.startswith(DOCS_PATHS):
            # La API solo devuelve JSON/CSV: no necesita cargar scripts, estilos ni ser embebida.
            response.headers["Content-Security-Policy"]="default-src 'none'; frame-ancestors 'none'"
        if request.url.path.startswith(settings.api_prefix):
            # Respuestas con datos personales: que ningún navegador ni proxy las guarde.
            response.headers["Cache-Control"]="no-store"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
        return response


class RateLimiter:
    """Ventana deslizante en memoria. Suficiente para una instancia; con varias réplicas usar Redis."""

    def __init__(self, limit: int, window_seconds: int, max_keys: int = 10_000):
        self.limit, self.window, self.max_keys = limit, window_seconds, max_keys
        self._hits: dict[str, deque] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        if len(self._hits) > self.max_keys:
            self._prune(now)
        return True

    def _prune(self, now: float):
        # Evita que la tabla crezca sin límite (cada IP nueva ocupa memoria).
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= now - self.window]:
            del self._hits[key]

    def reset(self):
        self._hits.clear()


auth_rate_limiter = RateLimiter(limit=10, window_seconds=60)


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Limita intentos de contraseña y de código 2FA por IP y por ruta."""
    PATHS = {LOGIN_PATH, VERIFY_2FA_PATH}

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path in self.PATHS:
            if not auth_rate_limiter.allow(f"{request.url.path}|{client_ip(request)}"):
                return JSONResponse({"detail":"Demasiados intentos. Intenta más tarde."}, status_code=429, headers={"Retry-After": str(auth_rate_limiter.window)})
        return await call_next(request)


class CSRFMiddleware(BaseHTTPMiddleware):
    SAFE={"GET","HEAD","OPTIONS"}
    EXEMPT={LOGIN_PATH, VERIFY_2FA_PATH}
    async def dispatch(self, request: Request, call_next):
        if request.method not in self.SAFE and request.url.path not in self.EXEMPT:
            cookie=request.cookies.get("inka_csrf","")
            header=request.headers.get("x-csrf-token","")
            # Se comparan bytes: compare_digest con texto no ASCII lanza TypeError (error 500).
            if not cookie or not header or not secrets.compare_digest(cookie.encode(),header.encode()):
                return JSONResponse({"detail":"CSRF token inválido"}, status_code=403)
        return await call_next(request)

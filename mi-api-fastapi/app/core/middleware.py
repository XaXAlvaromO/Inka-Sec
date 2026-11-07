import secrets, time
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["X-Frame-Options"]="DENY"
        response.headers["Referrer-Policy"]="no-referrer"
        response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
        return response

class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    buckets=defaultdict(deque)
    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/auth/login") and request.method=="POST":
            ip=(request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")).split(",")[0].strip()
            now=time.time(); q=self.buckets[ip]
            while q and q[0] < now-60: q.popleft()
            if len(q)>=10: return JSONResponse({"detail":"Demasiados intentos. Intenta más tarde."}, status_code=429)
            q.append(now)
        return await call_next(request)

class CSRFMiddleware(BaseHTTPMiddleware):
    SAFE={"GET","HEAD","OPTIONS"}
    EXEMPT={"/api/v1/auth/login","/api/v1/auth/2fa/verify"}
    async def dispatch(self, request: Request, call_next):
        if request.method not in self.SAFE and request.url.path not in self.EXEMPT:
            cookie=request.cookies.get("inka_csrf")
            header=request.headers.get("x-csrf-token")
            if not cookie or not header or not secrets.compare_digest(cookie,header):
                return JSONResponse({"detail":"CSRF token inválido"}, status_code=403)
        return await call_next(request)

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {
    "/health",
    "/",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
    "/api/auth/register-tenant",
    "/api/auth/login",
    "/api/admin/tenants",
}

IGNORED_SUBDOMAINS = {"www", "api", "erp", "app", "knooz1", "knooz", "balanced-tenderness"}

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip public paths
        if path in PUBLIC_PATHS or path.startswith("/api/admin/tenants"):
            return await call_next(request)

        slug = self._resolve_slug(request)
        if not slug:
            return await call_next(request)

        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT id, slug, is_active FROM public.tenants WHERE slug = :slug
            """), {"slug": slug})
            tenant = result.fetchone()

            if not tenant:
                return await call_next(request)

            if not tenant.is_active:
                return JSONResponse(status_code=403,
                    content={"detail": "This account is inactive. Contact support."})

            request.state.tenant_id = str(tenant.id)
            request.state.tenant_slug = tenant.slug
            db.execute(text(f'SET search_path TO "{tenant.slug}", public'))
            request.state.db = db

            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            return await call_next(request)
        finally:
            db.close()

    def _resolve_slug(self, request: Request):
        header_slug = request.headers.get("X-Tenant-Slug", "").strip().lower()
        if header_slug:
            return header_slug
        host = request.headers.get("host", "").split(":")[0]
        parts = host.split(".")
        if len(parts) >= 3:
            subdomain = parts[0].lower()
            if subdomain not in IGNORED_SUBDOMAINS:
                return subdomain
        return None

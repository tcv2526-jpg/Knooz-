from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

IGNORED_SUBDOMAINS = {
    "www", "api", "erp", "app", "knooz1", "knooz",
    "balanced-tenderness", "knooz-production"
}

BYPASS_PREFIXES = (
    "/health",
    "/",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
    "/api/admin/",
    "/api/auth/",
)


class TenantMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        # Bypass tenant resolution for public/admin paths
        if any(path == p or path.startswith(p) for p in BYPASS_PREFIXES):
            await self.app(scope, receive, send)
            return

        # Try to resolve slug from headers
        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode().split(":")[0]
        slug_header = headers.get(b"x-tenant-slug", b"").decode().strip().lower()

        slug = slug_header
        if not slug:
            parts = host.split(".")
            if len(parts) >= 3:
                subdomain = parts[0].lower()
                if subdomain not in IGNORED_SUBDOMAINS:
                    slug = subdomain

        if not slug:
            await self.app(scope, receive, send)
            return

        db = SessionLocal()
        try:
            result = db.execute(text(
                "SELECT id, slug, is_active FROM public.tenants WHERE slug = :slug"
            ), {"slug": slug})
            tenant = result.fetchone()

            if not tenant:
                await self.app(scope, receive, send)
                return

            if not tenant.is_active:
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "This account is inactive. Contact support."}
                )
                await response(scope, receive, send)
                return

            db.execute(text(f'SET search_path TO "{tenant.slug}", public'))
            scope["tenant_id"] = str(tenant.id)
            scope["tenant_slug"] = tenant.slug

            await self.app(scope, receive, send)

        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            await self.app(scope, receive, send)
        finally:
            db.close()

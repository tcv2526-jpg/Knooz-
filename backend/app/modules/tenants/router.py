from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import Optional
from passlib.context import CryptContext
from app.core.database import get_db
from app.modules.tenants.provisioning import (
    provision_tenant, deprovision_tenant, tenant_exists, list_tenants
)

router = APIRouter(prefix="/api/admin/tenants", tags=["Tenant Admin"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TenantCreate(BaseModel):
    name: str
    slug: str
    domain: Optional[str] = None
    plan: str = "starter"
    admin_email: EmailStr
    admin_name: str
    admin_password: str


@router.post("/", status_code=201)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    slug = payload.slug.lower().strip()
    if not slug.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "Slug must contain only letters, numbers, hyphens, underscores.")
    if tenant_exists(db, slug):
        raise HTTPException(409, f"Tenant '{slug}' already exists.")
    db.execute(text("""
        INSERT INTO public.tenants (name, slug, domain, plan)
        VALUES (:name, :slug, :domain, :plan)
    """), {"name": payload.name, "slug": slug, "domain": payload.domain, "plan": payload.plan})
    hashed = pwd_context.hash(payload.admin_password)
    provision_tenant(db=db, slug=slug, admin_email=payload.admin_email,
                     admin_name=payload.admin_name, admin_hashed_password=hashed)
    return {"message": f"Tenant '{slug}' provisioned successfully.",
            "slug": slug, "domain": payload.domain or f"{slug}.erp.tcv-ai.com"}


@router.get("/")
def get_all_tenants(db: Session = Depends(get_db)):
    tenants = list_tenants(db)
    return {"tenants": tenants, "total": len(tenants)}


@router.delete("/{slug}")
def remove_tenant(slug: str, db: Session = Depends(get_db)):
    if not tenant_exists(db, slug):
        raise HTTPException(404, f"Tenant '{slug}' not found.")
    deprovision_tenant(db, slug)
    return {"message": f"Tenant '{slug}' permanently removed."}


@router.patch("/{slug}/toggle")
def toggle_tenant(slug: str, db: Session = Depends(get_db)):
    result = db.execute(text("""
        UPDATE public.tenants SET is_active = NOT is_active
        WHERE slug = :slug RETURNING slug, is_active
    """), {"slug": slug})
    row = result.fetchone()
    if not row:
        raise HTTPException(404, f"Tenant '{slug}' not found.")
    db.commit()
    status = "activated" if row.is_active else "deactivated"
    return {"message": f"Tenant '{slug}' {status}.", "is_active": row.is_active}

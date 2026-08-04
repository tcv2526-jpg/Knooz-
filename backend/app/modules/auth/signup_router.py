from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.core.database import get_db
from app.modules.tenants.provisioning import provision_tenant, tenant_exists

router = APIRouter(prefix="/api/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TenantSignup(BaseModel):
    company_name: str
    slug: str
    admin_email: EmailStr
    admin_name: str
    admin_password: str
    plan: str = "trial"


@router.post("/register-tenant", status_code=201)
def register_tenant(payload: TenantSignup, db: Session = Depends(get_db)):
    slug = payload.slug.lower().strip()

    if not slug.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "Slug must contain only letters, numbers, hyphens, or underscores.")
    if len(slug) < 3 or len(slug) > 30:
        raise HTTPException(400, "Slug must be between 3 and 30 characters.")

    reserved = {"admin", "api", "www", "erp", "app", "knooz", "public", "superadmin"}
    if slug in reserved:
        raise HTTPException(400, "This name is reserved. Please choose another.")

    if tenant_exists(db, slug):
        raise HTTPException(409, "This company name is already taken. Please choose another.")

    db.execute(text(
        "INSERT INTO public.tenants (name, slug, plan) VALUES (:name, :slug, :plan)"
    ), {"name": payload.company_name, "slug": slug, "plan": "trial"})

    hashed = pwd_context.hash(payload.admin_password)
    provision_tenant(db=db, slug=slug, admin_email=payload.admin_email,
                     admin_name=payload.admin_name, admin_hashed_password=hashed)

    trial_end = datetime.utcnow() + timedelta(days=14)
    db.execute(text(
        "UPDATE public.tenants SET subscription_plan='trial', "
        "subscription_start=now(), subscription_end=:trial_end, price_sar=0 "
        "WHERE slug=:slug"
    ), {"trial_end": trial_end, "slug": slug})
    db.commit()

    return {
        "message": "Account created successfully! You have a 14-day free trial.",
        "slug": slug,
        "login_url": f"https://erp.tcv-ai.com/login?tenant={slug}",
        "company": payload.company_name,
        "trial_ends": str(trial_end.date()),
    }


@router.get("/check-slug/{slug}")
def check_slug(slug: str, db: Session = Depends(get_db)):
    slug = slug.lower().strip()
    reserved = {"admin", "api", "www", "erp", "app", "knooz", "public", "superadmin"}
    if slug in reserved or tenant_exists(db, slug):
        return {"available": False}
    return {"available": True}

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
    try:
        result = db.execute(text(
            "SELECT id, name, slug, domain, plan, is_active, created_at, "
            "COALESCE(subscription_plan, plan) as subscription_plan, "
            "subscription_end, COALESCE(price_sar, 0) as price_sar, "
            "CASE WHEN subscription_end > now() THEN true ELSE false END as is_valid, "
            "EXTRACT(DAY FROM subscription_end - now()) as days_remaining "
            "FROM public.tenants ORDER BY created_at DESC"
        ))
        tenants = [dict(row._mapping) for row in result.fetchall()]
    except Exception:
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

from datetime import datetime, timedelta

PLANS = {
    "monthly":   {"days": 30,  "price": 299},
    "biannual":  {"days": 180, "price": 1499},
    "annual":    {"days": 365, "price": 2499},
    "trial":     {"days": 14,  "price": 0},
}

class SubscriptionUpdate(BaseModel):
    plan: str
    start_date: Optional[str] = None

@router.post("/{slug}/subscribe")
def set_subscription(slug: str, payload: SubscriptionUpdate, db: Session = Depends(get_db)):
    """Set or renew a tenant subscription."""
    if payload.plan not in PLANS:
        raise HTTPException(400, f"Invalid plan. Choose from: {list(PLANS.keys())}")
    
    plan = PLANS[payload.plan]
    start = datetime.utcnow()
    end = start + timedelta(days=plan["days"])
    
    result = db.execute(text("""
        UPDATE public.tenants 
        SET subscription_plan = :plan,
            subscription_start = :start,
            subscription_end = :end,
            price_sar = :price,
            is_active = true
        WHERE slug = :slug
        RETURNING slug, subscription_plan, subscription_end, price_sar
    """), {"plan": payload.plan, "start": start, "end": end, 
           "price": plan["price"], "slug": slug})
    row = result.fetchone()
    if not row:
        raise HTTPException(404, f"Tenant '{slug}' not found.")
    db.commit()
    return {
        "message": f"Subscription set for '{slug}'",
        "plan": payload.plan,
        "expires": str(end.date()),
        "price_sar": plan["price"],
        "days": plan["days"],
    }

@router.get("/{slug}/subscription")
def get_subscription(slug: str, db: Session = Depends(get_db)):
    """Get subscription status for a tenant."""
    result = db.execute(text("""
        SELECT slug, name, plan, subscription_plan, subscription_start, 
               subscription_end, price_sar, is_active,
               CASE WHEN subscription_end > now() THEN true ELSE false END as is_valid,
               EXTRACT(DAY FROM subscription_end - now()) as days_remaining
        FROM public.tenants WHERE slug = :slug
    """), {"slug": slug})
    row = result.fetchone()
    if not row:
        raise HTTPException(404, f"Tenant '{slug}' not found.")
    return dict(row._mapping)

@router.post("/check-expiry")
def check_and_disable_expired(db: Session = Depends(get_db)):
    """Disable all tenants with expired subscriptions. Run daily via cron."""
    result = db.execute(text("""
        UPDATE public.tenants 
        SET is_active = false
        WHERE subscription_end < now() 
        AND subscription_end IS NOT NULL
        AND is_active = true
        RETURNING slug, subscription_end
    """))
    expired = [dict(row._mapping) for row in result.fetchall()]
    db.commit()
    return {"disabled": expired, "count": len(expired)}


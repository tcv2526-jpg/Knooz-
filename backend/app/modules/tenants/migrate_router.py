from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/api/admin/migrate", tags=["Migration"])

ZATCA_MIGRATION = """
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS invoice_type VARCHAR DEFAULT 'simplified',
    ADD COLUMN IF NOT EXISTS seller_vat VARCHAR,
    ADD COLUMN IF NOT EXISTS buyer_vat VARCHAR,
    ADD COLUMN IF NOT EXISTS buyer_address VARCHAR,
    ADD COLUMN IF NOT EXISTS supply_date DATE,
    ADD COLUMN IF NOT EXISTS zatca_qr TEXT,
    ADD COLUMN IF NOT EXISTS zatca_xml TEXT,
    ADD COLUMN IF NOT EXISTS zatca_hash VARCHAR,
    ADD COLUMN IF NOT EXISTS zatca_status VARCHAR DEFAULT 'pending';
"""

@router.post("/zatca/{slug}")
def migrate_zatca(slug: str, db: Session = Depends(get_db)):
    """Add ZATCA columns to an existing tenant schema."""
    try:
        db.execute(text(f'SET search_path TO "{slug}", public'))
        db.execute(text(ZATCA_MIGRATION))
        db.commit()
        return {"message": f"ZATCA columns added to tenant '{slug}' successfully"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}

SUBSCRIPTION_MIGRATION = """
ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR DEFAULT 'monthly',
    ADD COLUMN IF NOT EXISTS subscription_start TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS subscription_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS max_users INTEGER DEFAULT 5,
    ADD COLUMN IF NOT EXISTS price_sar FLOAT DEFAULT 0;
"""

@router.post("/subscription")
def migrate_subscription(db: Session = Depends(get_db)):
    """Add subscription columns to public.tenants table."""
    try:
        db.execute(text(SUBSCRIPTION_MIGRATION))
        db.commit()
        return {"message": "Subscription columns added successfully"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}

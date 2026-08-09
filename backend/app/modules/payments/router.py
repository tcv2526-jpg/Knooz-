from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import requests
import base64
import json
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.config import settings

router = APIRouter(prefix="/api/payments", tags=["Payments"])

PLANS = {
    "trial":    {"days": 14,  "price_halalas": 0,       "name": "Free Trial"},
    "monthly":  {"days": 30,  "price_halalas": 29900,   "name": "Monthly - SAR 299"},
    "biannual": {"days": 180, "price_halalas": 149900,  "name": "6 Months - SAR 1,499"},
    "annual":   {"days": 365, "price_halalas": 249900,  "name": "Annual - SAR 2,499"},
}


def moyasar_auth():
    key = settings.MOYASAR_SECRET_KEY
    encoded = base64.b64encode(f"{key}:".encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Content-Type": "application/json"}


class PaymentCreate(BaseModel):
    slug: str
    plan: str
    token: str          # Moyasar payment token from frontend
    callback_url: Optional[str] = None


class PaymentStatus(BaseModel):
    payment_id: str
    slug: str


@router.post("/create")
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db)):
    """Create a Moyasar payment for a subscription plan."""
    if payload.plan not in PLANS:
        raise HTTPException(400, f"Invalid plan: {payload.plan}")

    plan = PLANS[payload.plan]

    if plan["price_halalas"] == 0:
        # Free trial - activate immediately
        _activate_tenant(db, payload.slug, "trial", 14, 0)
        return {"status": "success", "message": "Free trial activated"}

    # Create payment with Moyasar
    payment_data = {
        "amount": plan["price_halalas"],
        "currency": "SAR",
        "description": f"Knooz ERP - {plan['name']} - {payload.slug}",
        "source": {
            "type": "token",
            "token": payload.token
        },
        "metadata": {
            "slug": payload.slug,
            "plan": payload.plan,
        }
    }

    try:
        response = requests.post(
            "https://api.moyasar.com/v1/payments",
            headers=moyasar_auth(),
            json=payment_data,
            timeout=30
        )
        result = response.json()

        if response.status_code in (200, 201) and result.get("status") == "paid":
            # Payment successful - activate tenant
            plan_info = PLANS[payload.plan]
            _activate_tenant(
                db, payload.slug, payload.plan,
                plan_info["days"], plan_info["price_halalas"] / 100
            )
            return {
                "status": "success",
                "payment_id": result.get("id"),
                "message": f"Payment successful! Your {payload.plan} plan is now active."
            }
        elif result.get("status") == "initiated":
            # 3D Secure required
            return {
                "status": "initiated",
                "payment_id": result.get("id"),
                "transaction_url": result.get("source", {}).get("transaction_url"),
                "message": "Please complete 3D Secure verification"
            }
        else:
            raise HTTPException(400, result.get("message", "Payment failed"))

    except requests.RequestException as e:
        raise HTTPException(500, f"Payment service error: {str(e)}")


@router.get("/verify/{payment_id}")
def verify_payment(payment_id: str, slug: str, plan: str, db: Session = Depends(get_db)):
    """Verify payment status after 3D Secure redirect."""
    try:
        response = requests.get(
            f"https://api.moyasar.com/v1/payments/{payment_id}",
            headers=moyasar_auth(),
            timeout=30
        )
        result = response.json()

        if result.get("status") == "paid":
            plan_info = PLANS.get(plan, PLANS["monthly"])
            _activate_tenant(
                db, slug, plan,
                plan_info["days"], plan_info["price_halalas"] / 100
            )
            return {"status": "success", "message": "Payment verified and account activated!"}
        else:
            return {"status": result.get("status"), "message": "Payment not completed"}

    except requests.RequestException as e:
        raise HTTPException(500, f"Verification error: {str(e)}")


@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    """Moyasar webhook for payment events."""
    body = await request.json()
    event_type = body.get("type")
    payment = body.get("data", {})

    if event_type == "payment_paid":
        metadata = payment.get("metadata", {})
        slug = metadata.get("slug")
        plan = metadata.get("plan", "monthly")
        if slug:
            plan_info = PLANS.get(plan, PLANS["monthly"])
            _activate_tenant(db, slug, plan, plan_info["days"], plan_info["price_halalas"] / 100)

    return {"received": True}


@router.get("/plans")
def get_plans():
    """Return available subscription plans."""
    return {
        "plans": [
            {"id": "trial",    "name": "Free Trial",  "price": 0,    "price_sar": "Free",      "days": 14,  "currency": "SAR"},
            {"id": "monthly",  "name": "Monthly",     "price": 299,  "price_sar": "SAR 299",   "days": 30,  "currency": "SAR"},
            {"id": "biannual", "name": "6 Months",    "price": 1499, "price_sar": "SAR 1,499", "days": 180, "currency": "SAR"},
            {"id": "annual",   "name": "Annual",      "price": 2499, "price_sar": "SAR 2,499", "days": 365, "currency": "SAR"},
        ]
    }


def _activate_tenant(db: Session, slug: str, plan: str, days: int, price: float):
    """Activate a tenant subscription."""
    end_date = datetime.utcnow() + timedelta(days=days)
    db.execute(text("""
        UPDATE public.tenants
        SET subscription_plan = :plan,
            subscription_start = now(),
            subscription_end = :end_date,
            price_sar = :price,
            is_active = true
        WHERE slug = :slug
    """), {"plan": plan, "end_date": end_date, "price": price, "slug": slug})
    db.commit()

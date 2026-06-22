from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.crm.models import Contact, Lead, Deal
from app.modules.crm.schemas import (
    ContactCreate, ContactOut, LeadCreate, LeadOut, DealCreate, DealOut
)

router = APIRouter(prefix="/api/crm", tags=["crm"])

# ── Contacts ──────────────────────────────────────────────
@router.get("/contacts", response_model=List[ContactOut])
def list_contacts(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Contact).order_by(Contact.created_at.desc()).all()

@router.post("/contacts", response_model=ContactOut, status_code=201)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = Contact(**contact.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.get("/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Contact).filter(Contact.id == contact_id).first()
    if not obj: raise HTTPException(404, "Contact not found")
    return obj

@router.put("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, data: ContactCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Contact).filter(Contact.id == contact_id).first()
    if not obj: raise HTTPException(404, "Contact not found")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Contact).filter(Contact.id == contact_id).first()
    if not obj: raise HTTPException(404, "Contact not found")
    db.delete(obj); db.commit()

# ── Leads ─────────────────────────────────────────────────
@router.get("/leads", response_model=List[LeadOut])
def list_leads(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Lead).order_by(Lead.created_at.desc()).all()

@router.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(lead: LeadCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = Lead(**lead.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, data: LeadCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Lead).filter(Lead.id == lead_id).first()
    if not obj: raise HTTPException(404, "Lead not found")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/leads/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Lead).filter(Lead.id == lead_id).first()
    if not obj: raise HTTPException(404, "Lead not found")
    db.delete(obj); db.commit()

# ── Deals ─────────────────────────────────────────────────
@router.get("/deals", response_model=List[DealOut])
def list_deals(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Deal).order_by(Deal.created_at.desc()).all()

@router.post("/deals", response_model=DealOut, status_code=201)
def create_deal(deal: DealCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = Deal(**deal.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/deals/{deal_id}", response_model=DealOut)
def update_deal(deal_id: int, data: DealCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Deal).filter(Deal.id == deal_id).first()
    if not obj: raise HTTPException(404, "Deal not found")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/deals/{deal_id}", status_code=204)
def delete_deal(deal_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Deal).filter(Deal.id == deal_id).first()
    if not obj: raise HTTPException(404, "Deal not found")
    db.delete(obj); db.commit()

@router.get("/stats")
def crm_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import func
    total_contacts = db.query(Contact).count()
    total_leads = db.query(Lead).count()
    total_deals = db.query(Deal).count()
    deal_value = db.query(func.sum(Deal.value)).scalar() or 0
    return {
        "total_contacts": total_contacts,
        "total_leads": total_leads,
        "total_deals": total_deals,
        "total_deal_value": deal_value,
    }

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.modules.crm.models import LeadStatus, DealStage

# ── Contacts ──────────────────────────────────────────────
class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    notes: Optional[str] = None

class ContactOut(ContactCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# ── Leads ─────────────────────────────────────────────────
class LeadCreate(BaseModel):
    title: str
    contact_id: Optional[int] = None
    status: LeadStatus = LeadStatus.new
    source: Optional[str] = None
    estimated_value: float = 0
    notes: Optional[str] = None

class LeadOut(LeadCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# ── Deals ─────────────────────────────────────────────────
class DealCreate(BaseModel):
    title: str
    contact_id: Optional[int] = None
    stage: DealStage = DealStage.prospecting
    value: float = 0
    close_date: Optional[datetime] = None
    notes: Optional[str] = None

class DealOut(DealCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

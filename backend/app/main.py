from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine

# Import all models so SQLAlchemy creates them
from app.modules.auth.models import User
from app.modules.crm.models import Contact, Lead, Deal
from app.modules.inventory.models import Product, Order, OrderItem
from app.modules.accounting.models import Invoice, InvoiceItem, Transaction, Account, Journal, JournalLine
from app.modules.hr.models import Employee, LeaveRequest, Payroll

# Import routers
from app.modules.auth.router import router as auth_router
from app.modules.crm.router import router as crm_router
from app.modules.inventory.router import router as inventory_router
from app.modules.accounting.router import router as accounting_router
from app.modules.hr.router import router as hr_router
from app.modules.ai.router import router as ai_router

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Knooz ERP",
    description="Full ERP system — CRM, Accounting, HR, Inventory",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(crm_router)
app.include_router(inventory_router)
app.include_router(accounting_router)
app.include_router(hr_router)
app.include_router(ai_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
def root():
    return {"message": "Knooz ERP API", "docs": "/api/docs"}

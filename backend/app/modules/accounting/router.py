from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.accounting.models import Invoice, InvoiceItem, Transaction, Account, Journal, JournalLine
from app.modules.auth.models import User

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


class InvoiceItemIn(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float
    total: float

class InvoiceCreate(BaseModel):
    invoice_number: Optional[str] = None
    client_name: str
    client_email: Optional[str] = None
    status: str = "draft"
    issue_date: date
    due_date: date
    subtotal: float = 0
    tax_rate: float = 15
    tax_amount: float = 0
    total: float = 0
    notes: Optional[str] = None
    items: List[InvoiceItemIn] = []
    invoice_type: str = "simplified"
    seller_vat: Optional[str] = None
    buyer_vat: Optional[str] = None
    buyer_address: Optional[str] = None
    supply_date: Optional[date] = None

class TransactionCreate(BaseModel):
    type: str
    amount: float
    description: str
    category: Optional[str] = None
    reference: Optional[str] = None
    date: date

class AccountCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    account_type: str
    balance: float = 0

class JournalLineIn(BaseModel):
    account_id: int
    description: Optional[str] = None
    debit: float = 0
    credit: float = 0

class JournalCreate(BaseModel):
    journal_number: Optional[str] = None
    journal_type: str = "general"
    date: date
    description: str
    reference: Optional[str] = None
    is_posted: bool = False
    total_debit: float = 0
    total_credit: float = 0
    lines: List[JournalLineIn] = []


def _invoice_dict(inv):
    return {
        "id": inv.id, "invoice_number": inv.invoice_number,
        "client_name": inv.client_name, "client_email": inv.client_email,
        "status": inv.status.value if hasattr(inv.status, 'value') else inv.status,
        "issue_date": str(inv.issue_date), "due_date": str(inv.due_date),
        "subtotal": inv.subtotal, "tax_rate": inv.tax_rate,
        "tax_amount": inv.tax_amount, "total": inv.total, "notes": inv.notes,
        "invoice_type": inv.invoice_type, "seller_vat": inv.seller_vat,
        "buyer_vat": inv.buyer_vat, "buyer_address": inv.buyer_address,
        "zatca_qr": inv.zatca_qr, "zatca_hash": inv.zatca_hash,
        "zatca_status": inv.zatca_status,
        "items": [{"id": i.id, "description": i.description,
                   "quantity": i.quantity, "unit_price": i.unit_price,
                   "total": i.total} for i in inv.items],
        "created_at": str(inv.created_at),
    }


@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [_invoice_dict(inv) for inv in db.query(Invoice).order_by(Invoice.created_at.desc()).all()]


@router.post("/invoices", status_code=201)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    from app.modules.accounting.zatca_service import generate_qr_code_value, generate_invoice_xml, compute_invoice_hash

    inv_number = payload.invoice_number or f"INV-{db.query(Invoice).count()+1:04d}"
    zatca_qr = zatca_xml = zatca_hash = None

    if payload.seller_vat:
        try:
            zatca_qr = generate_qr_code_value(
                seller_name=payload.client_name, vat_number=payload.seller_vat,
                invoice_date=str(payload.issue_date) + "T00:00:00Z",
                total_with_vat=payload.total, vat_amount=payload.tax_amount)
            items_data = [{"description": i.description, "quantity": i.quantity,
                           "unit_price": i.unit_price} for i in payload.items]
            zatca_xml = generate_invoice_xml(
                invoice_number=inv_number, issue_date=str(payload.issue_date),
                seller_name=payload.client_name, seller_vat=payload.seller_vat,
                seller_address="Saudi Arabia", buyer_name=payload.client_name,
                buyer_vat=payload.buyer_vat, buyer_address=payload.buyer_address,
                line_items=items_data, subtotal=payload.subtotal,
                tax_amount=payload.tax_amount, total=payload.total,
                invoice_type=payload.invoice_type)
            zatca_hash = compute_invoice_hash(zatca_xml)
        except Exception:
            pass

    invoice = Invoice(
        invoice_number=inv_number, client_name=payload.client_name,
        client_email=payload.client_email, status=payload.status,
        issue_date=payload.issue_date, due_date=payload.due_date,
        subtotal=payload.subtotal, tax_rate=payload.tax_rate,
        tax_amount=payload.tax_amount, total=payload.total, notes=payload.notes,
        invoice_type=payload.invoice_type, seller_vat=payload.seller_vat,
        buyer_vat=payload.buyer_vat, buyer_address=payload.buyer_address,
        supply_date=payload.supply_date, zatca_qr=zatca_qr,
        zatca_xml=zatca_xml, zatca_hash=zatca_hash,
        zatca_status="reported" if zatca_qr else "pending")
    db.add(invoice); db.flush()

    for item in payload.items:
        db.add(InvoiceItem(invoice_id=invoice.id, description=item.description,
                           quantity=item.quantity, unit_price=item.unit_price, total=item.total))
    db.commit(); db.refresh(invoice)
    return _invoice_dict(invoice)


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404, "Invoice not found")
    return _invoice_dict(inv)


@router.get("/invoices/{invoice_id}/xml")
def download_xml(invoice_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv or not inv.zatca_xml: raise HTTPException(404, "XML not available")
    return Response(content=inv.zatca_xml, media_type="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={inv.invoice_number}.xml"})


@router.put("/invoices/{invoice_id}/status")
def update_status(invoice_id: int, status: str, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404, "Not found")
    inv.status = status; db.commit()
    return {"message": "Updated"}


@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404, "Not found")
    db.delete(inv); db.commit()
    return {"message": "Deleted"}


@router.get("/transactions")
def list_transactions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Transaction).order_by(Transaction.date.desc()).all()

@router.post("/transactions", status_code=201)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    t = Transaction(**payload.dict()); db.add(t); db.commit(); db.refresh(t); return t

@router.delete("/transactions/{tid}")
def delete_transaction(tid: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    t = db.query(Transaction).filter(Transaction.id == tid).first()
    if not t: raise HTTPException(404, "Not found")
    db.delete(t); db.commit(); return {"message": "Deleted"}


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Account).order_by(Account.code).all()

@router.post("/accounts", status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    a = Account(**payload.dict()); db.add(a); db.commit(); db.refresh(a); return a


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy import func as sqlfunc
    paid = db.query(sqlfunc.sum(Invoice.total)).filter(Invoice.status == "paid").scalar() or 0
    outstanding = db.query(sqlfunc.sum(Invoice.total)).filter(
        Invoice.status.in_(["sent", "overdue"])).scalar() or 0
    expenses = db.query(sqlfunc.sum(Transaction.amount)).filter(
        Transaction.type == "expense").scalar() or 0
    return {"total_income": paid, "total_expenses": expenses,
            "net_profit": paid - expenses, "outstanding": outstanding,
            "paid_invoices": db.query(Invoice).filter(Invoice.status == "paid").count()}


@router.get("/journals")
def list_journals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Journal).order_by(Journal.date.desc()).all()

@router.post("/journals", status_code=201)
def create_journal(payload: JournalCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    j = Journal(journal_number=payload.journal_number or f"JRN-{db.query(Journal).count()+1:04d}",
                journal_type=payload.journal_type, date=payload.date,
                description=payload.description, reference=payload.reference,
                is_posted=payload.is_posted, total_debit=payload.total_debit,
                total_credit=payload.total_credit)
    db.add(j); db.flush()
    for line in payload.lines:
        db.add(JournalLine(journal_id=j.id, **line.dict()))
    db.commit(); db.refresh(j); return j

@router.get("/financial-statements")
def financial_statements(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy import func as sqlfunc
    accounts = db.query(Account).all()
    assets = [a for a in accounts if a.account_type == "asset"]
    liabilities = [a for a in accounts if a.account_type == "liability"]
    equity = [a for a in accounts if a.account_type == "equity"]
    income = [a for a in accounts if a.account_type == "income"]
    expenses = [a for a in accounts if a.account_type == "expense"]
    total_assets = sum(a.balance for a in assets)
    total_liabilities = sum(a.balance for a in liabilities)
    total_equity = sum(a.balance for a in equity)
    total_income = sum(a.balance for a in income)
    total_expenses = sum(a.balance for a in expenses)
    # Also sum from transactions
    t_income = db.query(sqlfunc.sum(Transaction.amount)).filter(Transaction.type == "income").scalar() or 0
    t_expenses = db.query(sqlfunc.sum(Transaction.amount)).filter(Transaction.type == "expense").scalar() or 0
    paid_invoices = db.query(sqlfunc.sum(Invoice.total)).filter(Invoice.status == "paid").scalar() or 0
    return {
        "balance_sheet": {
            "assets": [{"code": a.code, "name": a.name, "name_ar": a.name_ar, "balance": a.balance} for a in assets],
            "liabilities": [{"code": a.code, "name": a.name, "name_ar": a.name_ar, "balance": a.balance} for a in liabilities],
            "equity": [{"code": a.code, "name": a.name, "name_ar": a.name_ar, "balance": a.balance} for a in equity],
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
        },
        "profit_loss": {
            "income": [{"code": a.code, "name": a.name, "name_ar": a.name_ar, "balance": a.balance} for a in income],
            "expenses": [{"code": a.code, "name": a.name, "name_ar": a.name_ar, "balance": a.balance} for a in expenses],
            "total_income": t_income + paid_invoices,
            "total_expenses": t_expenses + total_expenses,
            "net_profit": (t_income + paid_invoices) - (t_expenses + total_expenses),
        },
        "trial_balance": [{"code": a.code, "name": a.name, "type": a.account_type, "balance": a.balance} for a in accounts],
    }


@router.get("/ledger")
def get_ledger(account_id: int = None, date_from: str = None, date_to: str = None,
               db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(JournalLine).join(Journal)
    if account_id:
        query = query.filter(JournalLine.account_id == account_id)
    lines = query.order_by(Journal.date).all()
    result = []
    running_balance = 0
    for line in lines:
        running_balance += line.debit - line.credit
        result.append({
            "journal_id": line.journal_id,
            "date": str(line.journal.date),
            "description": line.journal.description,
            "reference": line.journal.reference,
            "account_id": line.account_id,
            "debit": line.debit,
            "credit": line.credit,
            "balance": running_balance,
        })
    return {"lines": result, "closing_balance": running_balance}

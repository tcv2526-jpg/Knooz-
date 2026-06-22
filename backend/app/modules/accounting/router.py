from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.accounting.models import (
    Invoice, InvoiceItem, Transaction, Account, Journal, JournalLine,
    InvoiceStatus, TransactionType, JournalType
)
import random, string

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


def gen_invoice_number():
    return "INV-" + "".join(random.choices(string.digits, k=5))

def gen_journal_number():
    return "JE-" + "".join(random.choices(string.digits, k=6))


# ── Schemas ───────────────────────────────────────────────
class InvoiceItemIn(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float

class InvoiceCreate(BaseModel):
    client_name: str
    client_email: Optional[str] = None
    issue_date: date
    due_date: date
    tax_rate: float = 15
    notes: Optional[str] = None
    items: List[InvoiceItemIn]

class InvoiceItemOut(BaseModel):
    id: int; description: str; quantity: float; unit_price: float; total: float
    class Config: from_attributes = True

class InvoiceOut(BaseModel):
    id: int; invoice_number: str; client_name: str; client_email: Optional[str]
    status: InvoiceStatus; issue_date: date; due_date: date
    subtotal: float; tax_rate: float; tax_amount: float; total: float
    notes: Optional[str]; items: List[InvoiceItemOut]; created_at: datetime
    class Config: from_attributes = True

class TransactionCreate(BaseModel):
    type: TransactionType; amount: float; description: str
    category: Optional[str] = None; reference: Optional[str] = None; date: date

class TransactionOut(TransactionCreate):
    id: int; created_at: datetime
    class Config: from_attributes = True

class AccountCreate(BaseModel):
    code: str; name: str; name_ar: Optional[str] = None
    account_type: str; balance: float = 0

class AccountOut(AccountCreate):
    id: int; is_active: bool; created_at: datetime
    class Config: from_attributes = True

class JournalLineIn(BaseModel):
    account_id: int; description: Optional[str] = None
    debit: float = 0; credit: float = 0

class JournalCreate(BaseModel):
    journal_type: JournalType = JournalType.general
    date: date; description: str; reference: Optional[str] = None
    lines: List[JournalLineIn]

class JournalLineOut(BaseModel):
    id: int; account_id: int; description: Optional[str]
    debit: float; credit: float
    account: Optional[AccountOut] = None
    class Config: from_attributes = True

class JournalOut(BaseModel):
    id: int; journal_number: str; journal_type: JournalType
    date: date; description: str; reference: Optional[str]
    is_posted: bool; total_debit: float; total_credit: float
    lines: List[JournalLineOut]; created_at: datetime
    class Config: from_attributes = True


# ── Invoices ──────────────────────────────────────────────
@router.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Invoice).order_by(Invoice.created_at.desc()).all()

@router.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(inv: InvoiceCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    subtotal = sum(i.quantity * i.unit_price for i in inv.items)
    tax_amount = subtotal * inv.tax_rate / 100
    obj = Invoice(invoice_number=gen_invoice_number(), client_name=inv.client_name,
        client_email=inv.client_email, issue_date=inv.issue_date, due_date=inv.due_date,
        tax_rate=inv.tax_rate, subtotal=subtotal, tax_amount=tax_amount,
        total=subtotal+tax_amount, notes=inv.notes)
    db.add(obj); db.flush()
    for item in inv.items:
        db.add(InvoiceItem(invoice_id=obj.id, description=item.description,
            quantity=item.quantity, unit_price=item.unit_price,
            total=item.quantity*item.unit_price))
    db.commit(); db.refresh(obj)
    return obj

@router.put("/invoices/{invoice_id}/status")
def update_invoice_status(invoice_id: int, status: InvoiceStatus, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not obj: raise HTTPException(404, "Invoice not found")
    obj.status = status; db.commit()
    return {"id": obj.id, "status": obj.status}

@router.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not obj: raise HTTPException(404, "Invoice not found")
    db.delete(obj); db.commit()


# ── Transactions ──────────────────────────────────────────
@router.get("/transactions", response_model=List[TransactionOut])
def list_transactions(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Transaction).order_by(Transaction.date.desc()).all()

@router.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(tx: TransactionCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = Transaction(**tx.model_dump()); db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not obj: raise HTTPException(404, "Not found")
    db.delete(obj); db.commit()


# ── Chart of Accounts ─────────────────────────────────────
@router.get("/accounts", response_model=List[AccountOut])
def list_accounts(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Account).order_by(Account.code).all()

@router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(acc: AccountCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Account).filter(Account.code == acc.code).first():
        raise HTTPException(400, "Account code already exists")
    obj = Account(**acc.model_dump()); db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Account).filter(Account.id == account_id).first()
    if not obj: raise HTTPException(404, "Account not found")
    db.delete(obj); db.commit()

@router.post("/accounts/seed")
def seed_accounts(db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Account).count() > 0:
        return {"message": "Accounts already seeded"}
    default_accounts = [
        ("1000","Cash","النقدية","asset"),("1100","Accounts Receivable","حسابات القبض","asset"),
        ("1200","Inventory","المخزون","asset"),("1300","Prepaid Expenses","المصروفات المدفوعة مقدماً","asset"),
        ("1500","Fixed Assets","الأصول الثابتة","asset"),
        ("2000","Accounts Payable","حسابات الدفع","liability"),("2100","Accrued Expenses","المصروفات المستحقة","liability"),
        ("2200","VAT Payable","ضريبة القيمة المضافة المستحقة","liability"),("2500","Loans Payable","القروض","liability"),
        ("3000","Owner Equity","حقوق المالك","equity"),("3100","Retained Earnings","الأرباح المحتجزة","equity"),
        ("4000","Sales Revenue","إيرادات المبيعات","income"),("4100","Service Revenue","إيرادات الخدمات","income"),
        ("4200","Other Income","إيرادات أخرى","income"),
        ("5000","Cost of Goods Sold","تكلفة البضاعة المباعة","expense"),("5100","Salaries Expense","مصروف الرواتب","expense"),
        ("5200","Rent Expense","مصروف الإيجار","expense"),("5300","Utilities Expense","مصروف المرافق","expense"),
        ("5400","Marketing Expense","مصروف التسويق","expense"),("5500","Other Expenses","مصروفات أخرى","expense"),
    ]
    for code, name, name_ar, atype in default_accounts:
        db.add(Account(code=code, name=name, name_ar=name_ar, account_type=atype))
    db.commit()
    return {"message": f"Seeded {len(default_accounts)} accounts"}


# ── Journal Entries ───────────────────────────────────────
@router.get("/journals", response_model=List[JournalOut])
def list_journals(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Journal).order_by(Journal.created_at.desc()).all()

@router.post("/journals", response_model=JournalOut, status_code=201)
def create_journal(j: JournalCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    total_debit = sum(l.debit for l in j.lines)
    total_credit = sum(l.credit for l in j.lines)
    if round(total_debit, 2) != round(total_credit, 2):
        raise HTTPException(400, f"Journal not balanced: debit {total_debit} ≠ credit {total_credit}")
    obj = Journal(journal_number=gen_journal_number(), journal_type=j.journal_type,
        date=j.date, description=j.description, reference=j.reference,
        total_debit=total_debit, total_credit=total_credit)
    db.add(obj); db.flush()
    for line in j.lines:
        db.add(JournalLine(journal_id=obj.id, account_id=line.account_id,
            description=line.description, debit=line.debit, credit=line.credit))
        account = db.query(Account).filter(Account.id == line.account_id).first()
        if account:
            account.balance += line.debit - line.credit
    db.commit(); db.refresh(obj)
    return obj

@router.put("/journals/{journal_id}/post")
def post_journal(journal_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Journal).filter(Journal.id == journal_id).first()
    if not obj: raise HTTPException(404, "Journal not found")
    obj.is_posted = True; db.commit()
    return {"id": obj.id, "is_posted": True}

@router.delete("/journals/{journal_id}", status_code=204)
def delete_journal(journal_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Journal).filter(Journal.id == journal_id).first()
    if not obj: raise HTTPException(404, "Journal not found")
    if obj.is_posted: raise HTTPException(400, "Cannot delete posted journal")
    db.delete(obj); db.commit()


# ── Financial Reports ─────────────────────────────────────
@router.get("/reports/balance-sheet")
def balance_sheet(db: Session = Depends(get_db), _=Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.is_active == True).all()
    assets = [a for a in accounts if a.account_type == "asset"]
    liabilities = [a for a in accounts if a.account_type == "liability"]
    equity = [a for a in accounts if a.account_type == "equity"]
    return {
        "assets": [{"id":a.id,"code":a.code,"name":a.name,"name_ar":a.name_ar,"balance":a.balance} for a in assets],
        "liabilities": [{"id":a.id,"code":a.code,"name":a.name,"name_ar":a.name_ar,"balance":a.balance} for a in liabilities],
        "equity": [{"id":a.id,"code":a.code,"name":a.name,"name_ar":a.name_ar,"balance":a.balance} for a in equity],
        "total_assets": sum(a.balance for a in assets),
        "total_liabilities": sum(a.balance for a in liabilities),
        "total_equity": sum(a.balance for a in equity),
    }

@router.get("/reports/profit-loss")
def profit_loss(db: Session = Depends(get_db), _=Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.is_active == True).all()
    income_accounts = [a for a in accounts if a.account_type == "income"]
    expense_accounts = [a for a in accounts if a.account_type == "expense"]
    total_income = sum(a.balance for a in income_accounts)
    total_expenses = sum(abs(a.balance) for a in expense_accounts)
    return {
        "income": [{"id":a.id,"code":a.code,"name":a.name,"name_ar":a.name_ar,"balance":a.balance} for a in income_accounts],
        "expenses": [{"id":a.id,"code":a.code,"name":a.name,"name_ar":a.name_ar,"balance":abs(a.balance)} for a in expense_accounts],
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": total_income - total_expenses,
    }

@router.get("/reports/trial-balance")
def trial_balance(db: Session = Depends(get_db), _=Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.is_active == True).all()
    rows = []
    for a in accounts:
        debit = a.balance if a.balance > 0 else 0
        credit = abs(a.balance) if a.balance < 0 else 0
        rows.append({"code":a.code,"name":a.name,"name_ar":a.name_ar,
                     "account_type":a.account_type,"debit":debit,"credit":credit})
    total_debit = sum(r["debit"] for r in rows)
    total_credit = sum(r["credit"] for r in rows)
    return {"rows": rows, "total_debit": total_debit, "total_credit": total_credit}


# ── Stats ─────────────────────────────────────────────────
@router.get("/stats")
def accounting_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    income = db.query(func.sum(Transaction.amount)).filter(Transaction.type == TransactionType.income).scalar() or 0
    expense = db.query(func.sum(Transaction.amount)).filter(Transaction.type == TransactionType.expense).scalar() or 0
    return {
        "total_invoices": db.query(Invoice).count(),
        "paid_invoices": db.query(Invoice).filter(Invoice.status == InvoiceStatus.paid).count(),
        "total_income": income, "total_expenses": expense,
        "net_profit": income - expense,
        "outstanding_amount": db.query(func.sum(Invoice.total)).filter(Invoice.status.in_([InvoiceStatus.sent, InvoiceStatus.overdue])).scalar() or 0,
        "total_journals": db.query(Journal).count(),
        "posted_journals": db.query(Journal).filter(Journal.is_posted == True).count(),
    }


@router.get("/reports/general-ledger")
def general_ledger(account_id: int = None, db: Session = Depends(get_db), _=Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.is_active == True).order_by(Account.code).all()
    result = []
    for acc in accounts:
        if account_id and acc.id != account_id:
            continue
        lines = db.query(JournalLine).filter(
            JournalLine.account_id == acc.id
        ).join(Journal).order_by(Journal.date).all()
        entries = []
        running_balance = 0
        for line in lines:
            running_balance += line.debit - line.credit
            entries.append({
                "journal_number": line.journal.journal_number,
                "date": str(line.journal.date),
                "description": line.description or line.journal.description,
                "debit": line.debit,
                "credit": line.credit,
                "balance": running_balance,
                "is_posted": line.journal.is_posted,
            })
        result.append({
            "account_id": acc.id,
            "code": acc.code,
            "name": acc.name,
            "name_ar": acc.name_ar,
            "account_type": acc.account_type,
            "opening_balance": acc.balance,
            "entries": entries,
            "total_debit": sum(e["debit"] for e in entries),
            "total_credit": sum(e["credit"] for e in entries),
            "closing_balance": acc.balance + sum(e["debit"] - e["credit"] for e in entries),
        })
    return {"accounts": result, "total_accounts": len(result)}

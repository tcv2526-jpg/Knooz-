from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.accounting.models import Account, Invoice, InvoiceItem, Transaction, Journal, JournalLine
from app.modules.auth.models import User

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


# ── CHART OF ACCOUNTS ─────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    description_ar: Optional[str] = None
    account_type: str
    parent_code: Optional[str] = None
    opening_balance: float = 0
    allow_posting: bool = True

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    description_ar: Optional[str] = None
    account_type: Optional[str] = None
    opening_balance: Optional[float] = None
    allow_posting: Optional[bool] = None
    is_active: Optional[bool] = None


def get_level_from_code(code: str) -> int:
    length = len(code)
    if length <= 1: return 1
    if length <= 3: return 2
    if length <= 6: return 3
    if length <= 7: return 4
    if length <= 10: return 5
    return 6


def get_parent_code(code: str) -> Optional[str]:
    """Derive parent code from account code."""
    length = len(code)
    if length <= 1: return None
    if length <= 3: return code[:1]
    if length <= 6: return code[:3]
    if length <= 7: return code[:6]
    if length <= 10: return code[:7]
    return code[:10]


def compute_account_balance(db: Session, code: str) -> dict:
    """Recursively compute balance by summing all children."""
    # Check if this account has children
    children = db.query(Account).filter(Account.parent_code == code).all()
    if not children:
        # Leaf account - return its own balance
        acc = db.query(Account).filter(Account.code == code).first()
        if acc:
            return {"debit": acc.debit or 0, "credit": acc.credit or 0, "balance": (acc.debit or 0) - (acc.credit or 0)}
        return {"debit": 0, "credit": 0, "balance": 0}
    
    total_debit = 0
    total_credit = 0
    for child in children:
        child_bal = compute_account_balance(db, child.code)
        total_debit += child_bal["debit"]
        total_credit += child_bal["credit"]
    return {"debit": total_debit, "credit": total_credit, "balance": total_debit - total_credit}


def build_tree(accounts: list, parent_code=None) -> list:
    """Build hierarchical tree from flat list."""
    tree = []
    for acc in accounts:
        if acc["parent_code"] == parent_code:
            children = build_tree(accounts, acc["code"])
            acc["children"] = children
            # Auto-sum from children
            if children:
                acc["debit"] = sum(c["debit"] for c in children)
                acc["credit"] = sum(c["credit"] for c in children)
                acc["balance"] = acc["debit"] - acc["credit"]
            tree.append(acc)
    return sorted(tree, key=lambda x: x["code"])


@router.get("/accounts")
def list_accounts(tree: bool = True, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    accounts = db.query(Account).order_by(Account.code).all()
    flat = []
    for a in accounts:
        flat.append({
            "id": a.id, "code": a.code, "name": a.name, "name_ar": a.name_ar,
            "description_ar": a.description_ar, "account_type": a.account_type,
            "parent_code": a.parent_code, "level": a.level,
            "balance": (a.debit or 0) - (a.credit or 0),
            "opening_balance": a.opening_balance or 0,
            "debit": a.debit or 0, "credit": a.credit or 0,
            "is_active": a.is_active, "is_posted": a.is_posted,
            "allow_posting": a.allow_posting,
        })
    if tree:
        return {"accounts": build_tree(flat), "flat": flat}
    return {"accounts": flat}


@router.post("/accounts", status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    if db.query(Account).filter(Account.code == payload.code).first():
        raise HTTPException(400, f"Account code {payload.code} already exists")
    level = get_level_from_code(payload.code)
    parent_code = payload.parent_code or get_parent_code(payload.code)
    acc = Account(
        code=payload.code, name=payload.name, name_ar=payload.name_ar,
        description_ar=payload.description_ar, account_type=payload.account_type,
        parent_code=parent_code, level=level,
        opening_balance=payload.opening_balance,
        debit=payload.opening_balance if payload.opening_balance > 0 else 0,
        allow_posting=payload.allow_posting,
    )
    db.add(acc); db.commit(); db.refresh(acc)
    return acc


@router.put("/accounts/{account_id}")
def update_account(account_id: int, payload: AccountUpdate,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc: raise HTTPException(404, "Account not found")
    if acc.is_posted:
        raise HTTPException(403, "Account is posted. Admin must reopen it first.")
    for field, value in payload.dict(exclude_none=True).items():
        setattr(acc, field, value)
    db.commit(); db.refresh(acc)
    return acc


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc: raise HTTPException(404, "Account not found")
    if acc.is_posted:
        raise HTTPException(403, "Cannot delete a posted account.")
    # Check if has children
    children = db.query(Account).filter(Account.parent_code == acc.code).count()
    if children > 0:
        raise HTTPException(400, "Cannot delete account with sub-accounts.")
    db.delete(acc); db.commit()
    return {"message": "Account deleted"}


@router.post("/accounts/{account_id}/post")
def post_account(account_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc: raise HTTPException(404, "Not found")
    acc.is_posted = True
    db.commit()
    return {"message": f"Account {acc.code} posted", "is_posted": True}


@router.post("/accounts/{account_id}/reopen")
def reopen_account(account_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(403, "Only admins can reopen posted accounts.")
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc: raise HTTPException(404, "Not found")
    acc.is_posted = False
    db.commit()
    return {"message": f"Account {acc.code} reopened", "is_posted": False}


# ── INVOICES ──────────────────────────────────────────────────────────────────

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

class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    status: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total: Optional[float] = None
    notes: Optional[str] = None
    seller_vat: Optional[str] = None
    buyer_vat: Optional[str] = None


def _invoice_dict(inv):
    return {
        "id": inv.id, "invoice_number": inv.invoice_number,
        "client_name": inv.client_name, "client_email": inv.client_email,
        "status": inv.status.value if hasattr(inv.status, "value") else inv.status,
        "issue_date": str(inv.issue_date), "due_date": str(inv.due_date),
        "subtotal": inv.subtotal, "tax_rate": inv.tax_rate,
        "tax_amount": inv.tax_amount, "total": inv.total, "notes": inv.notes,
        "invoice_type": inv.invoice_type, "seller_vat": inv.seller_vat,
        "buyer_vat": inv.buyer_vat, "buyer_address": inv.buyer_address,
        "zatca_qr": inv.zatca_qr, "zatca_hash": inv.zatca_hash,
        "zatca_status": inv.zatca_status, "is_posted": inv.is_posted,
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


@router.put("/invoices/{invoice_id}")
def update_invoice(invoice_id: int, payload: InvoiceUpdate,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404, "Invoice not found")
    if inv.is_posted:
        raise HTTPException(403, "Invoice is posted. Admin must reopen it first.")
    for field, value in payload.dict(exclude_none=True).items():
        setattr(inv, field, value)
    db.commit(); db.refresh(inv)
    return _invoice_dict(inv)


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404, "Invoice not found")
    return _invoice_dict(inv)


@router.post("/invoices/{invoice_id}/post")
def post_invoice(invoice_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404, "Not found")
    if inv.is_posted: raise HTTPException(400, "Already posted")
    inv.is_posted = True
    inv.status = "sent"
    db.commit()
    return {"message": "Invoice posted", "is_posted": True}


@router.post("/invoices/{invoice_id}/reopen")
def reopen_invoice(invoice_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(403, "Only admins can reopen posted invoices.")
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404, "Not found")
    inv.is_posted = False
    db.commit()
    return {"message": "Invoice reopened", "is_posted": False}


@router.put("/invoices/{invoice_id}/status")
def update_invoice_status(invoice_id: int, status: str,
                          db: Session = Depends(get_db),
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
    if inv.is_posted:
        raise HTTPException(403, "Cannot delete a posted invoice.")
    db.delete(inv); db.commit()
    return {"message": "Deleted"}


@router.get("/invoices/{invoice_id}/xml")
def download_xml(invoice_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv or not inv.zatca_xml: raise HTTPException(404, "XML not available")
    return Response(content=inv.zatca_xml, media_type="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={inv.invoice_number}.xml"})


# ── TRANSACTIONS ──────────────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    type: str
    amount: float
    description: str
    category: Optional[str] = None
    reference: Optional[str] = None
    date: date
    account_code: Optional[str] = None

class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    reference: Optional[str] = None
    date: Optional[date] = None
    account_code: Optional[str] = None


@router.get("/transactions")
def list_transactions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Transaction).order_by(Transaction.date.desc()).all()

@router.post("/transactions", status_code=201)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    t = Transaction(**payload.dict()); db.add(t); db.commit(); db.refresh(t); return t

@router.put("/transactions/{tid}")
def update_transaction(tid: int, payload: TransactionUpdate,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    t = db.query(Transaction).filter(Transaction.id == tid).first()
    if not t: raise HTTPException(404, "Not found")
    if t.is_posted: raise HTTPException(403, "Transaction is posted. Admin must reopen first.")
    for field, value in payload.dict(exclude_none=True).items():
        setattr(t, field, value)
    db.commit(); db.refresh(t); return t

@router.post("/transactions/{tid}/post")
def post_transaction(tid: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    t = db.query(Transaction).filter(Transaction.id == tid).first()
    if not t: raise HTTPException(404, "Not found")
    if t.is_posted: raise HTTPException(400, "Already posted")
    # Update account balance
    if t.account_code:
        acc = db.query(Account).filter(Account.code == t.account_code).first()
        if acc:
            if t.type == "income":
                acc.credit += t.amount
            else:
                acc.debit += t.amount
    t.is_posted = True; db.commit()
    return {"message": "Posted", "is_posted": True}

@router.post("/transactions/{tid}/reopen")
def reopen_transaction(tid: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(403, "Only admins can reopen posted transactions.")
    t = db.query(Transaction).filter(Transaction.id == tid).first()
    if not t: raise HTTPException(404, "Not found")
    t.is_posted = False; db.commit()
    return {"message": "Reopened", "is_posted": False}

@router.delete("/transactions/{tid}")
def delete_transaction(tid: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    t = db.query(Transaction).filter(Transaction.id == tid).first()
    if not t: raise HTTPException(404, "Not found")
    if t.is_posted: raise HTTPException(403, "Cannot delete posted transaction.")
    db.delete(t); db.commit(); return {"message": "Deleted"}


# ── JOURNALS ──────────────────────────────────────────────────────────────────

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
    lines: List[JournalLineIn] = []

class JournalUpdate(BaseModel):
    journal_type: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None
    reference: Optional[str] = None


@router.get("/journals")
def list_journals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    journals = db.query(Journal).order_by(Journal.date.desc()).all()
    result = []
    for j in journals:
        result.append({
            "id": j.id, "journal_number": j.journal_number,
            "journal_type": j.journal_type.value if hasattr(j.journal_type, "value") else j.journal_type,
            "date": str(j.date), "description": j.description,
            "reference": j.reference, "is_posted": j.is_posted,
            "total_debit": j.total_debit, "total_credit": j.total_credit,
            "lines": [{"id": l.id, "account_id": l.account_id,
                       "description": l.description, "debit": l.debit,
                       "credit": l.credit} for l in j.lines],
        })
    return result

@router.post("/journals", status_code=201)
def create_journal(payload: JournalCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    total_debit = sum(l.debit for l in payload.lines)
    total_credit = sum(l.credit for l in payload.lines)
    if payload.lines and abs(total_debit - total_credit) > 0.01:
        raise HTTPException(400, f"Journal not balanced. Debit={total_debit}, Credit={total_credit}")
    j = Journal(
        journal_number=payload.journal_number or f"JRN-{db.query(Journal).count()+1:04d}",
        journal_type=payload.journal_type, date=payload.date,
        description=payload.description, reference=payload.reference,
        total_debit=total_debit, total_credit=total_credit)
    db.add(j); db.flush()
    for line in payload.lines:
        db.add(JournalLine(journal_id=j.id, **line.dict()))
    db.commit(); db.refresh(j)
    return j

@router.put("/journals/{journal_id}")
def update_journal(journal_id: int, payload: JournalUpdate,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    j = db.query(Journal).filter(Journal.id == journal_id).first()
    if not j: raise HTTPException(404, "Not found")
    if j.is_posted: raise HTTPException(403, "Journal is posted. Admin must reopen first.")
    for field, value in payload.dict(exclude_none=True).items():
        setattr(j, field, value)
    db.commit(); db.refresh(j); return j

@router.post("/journals/{journal_id}/post")
def post_journal(journal_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    j = db.query(Journal).filter(Journal.id == journal_id).first()
    if not j: raise HTTPException(404, "Not found")
    if j.is_posted: raise HTTPException(400, "Already posted")
    # Update account balances
    for line in j.lines:
        acc = db.query(Account).filter(Account.id == line.account_id).first()
        if acc:
            acc.debit += line.debit
            acc.credit += line.credit
            acc.balance = acc.debit - acc.credit
    j.is_posted = True; db.commit()
    return {"message": "Journal posted", "is_posted": True}

@router.post("/journals/{journal_id}/reopen")
def reopen_journal(journal_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(403, "Only admins can reopen posted journals.")
    j = db.query(Journal).filter(Journal.id == journal_id).first()
    if not j: raise HTTPException(404, "Not found")
    # Reverse account balances
    for line in j.lines:
        acc = db.query(Account).filter(Account.id == line.account_id).first()
        if acc:
            acc.debit -= line.debit
            acc.credit -= line.credit
            acc.balance = acc.debit - acc.credit
    j.is_posted = False; db.commit()
    return {"message": "Journal reopened", "is_posted": False}

@router.delete("/journals/{journal_id}")
def delete_journal(journal_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    j = db.query(Journal).filter(Journal.id == journal_id).first()
    if not j: raise HTTPException(404, "Not found")
    if j.is_posted: raise HTTPException(403, "Cannot delete posted journal.")
    db.delete(j); db.commit(); return {"message": "Deleted"}


# ── STATS ─────────────────────────────────────────────────────────────────────

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


@router.get("/financial-statements")
def financial_statements(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy import func as sqlfunc
    accounts = db.query(Account).all()
    assets = [a for a in accounts if a.account_type == "asset"]
    liabilities = [a for a in accounts if a.account_type == "liability"]
    equity = [a for a in accounts if a.account_type == "equity"]
    income = [a for a in accounts if a.account_type == "income"]
    expenses = [a for a in accounts if a.account_type == "expense"]
    t_income = db.query(sqlfunc.sum(Transaction.amount)).filter(Transaction.type == "income").scalar() or 0
    t_expenses = db.query(sqlfunc.sum(Transaction.amount)).filter(Transaction.type == "expense").scalar() or 0
    paid_invoices = db.query(sqlfunc.sum(Invoice.total)).filter(Invoice.status == "paid").scalar() or 0
    def acc_list(lst):
        return [{"code": a.code, "name": a.name, "name_ar": a.name_ar,
                 "balance": (a.debit or 0) - (a.credit or 0)} for a in lst]
    return {
        "balance_sheet": {
            "assets": acc_list(assets), "liabilities": acc_list(liabilities),
            "equity": acc_list(equity),
            "total_assets": sum((a.debit or 0) - (a.credit or 0) for a in assets),
            "total_liabilities": sum((a.debit or 0) - (a.credit or 0) for a in liabilities),
            "total_equity": sum((a.debit or 0) - (a.credit or 0) for a in equity),
        },
        "profit_loss": {
            "income": acc_list(income), "expenses": acc_list(expenses),
            "total_income": t_income + paid_invoices,
            "total_expenses": t_expenses,
            "net_profit": (t_income + paid_invoices) - t_expenses,
        },
        "trial_balance": acc_list(accounts),
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
            "journal_id": line.journal_id, "date": str(line.journal.date),
            "description": line.journal.description, "reference": line.journal.reference,
            "account_id": line.account_id, "debit": line.debit,
            "credit": line.credit, "balance": running_balance,
        })
    return {"lines": result, "closing_balance": running_balance}

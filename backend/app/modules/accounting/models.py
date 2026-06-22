from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text, ForeignKey, Date, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class JournalType(str, enum.Enum):
    sale = "sale"
    purchase = "purchase"
    bank = "bank"
    cash = "cash"
    general = "general"


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True)
    client_name = Column(String, nullable=False)
    client_email = Column(String)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    subtotal = Column(Float, default=0)
    tax_rate = Column(Float, default=15)
    tax_amount = Column(Float, default=0)
    total = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    description = Column(String, nullable=False)
    quantity = Column(Float, default=1)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    invoice = relationship("Invoice", back_populates="items")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String)
    reference = Column(String)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    name_ar = Column(String)
    account_type = Column(String, nullable=False)  # asset, liability, equity, income, expense
    balance = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    journal_lines = relationship("JournalLine", back_populates="account")


class Journal(Base):
    __tablename__ = "journals"
    id = Column(Integer, primary_key=True, index=True)
    journal_number = Column(String, unique=True, index=True)
    journal_type = Column(Enum(JournalType), default=JournalType.general)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    reference = Column(String)
    is_posted = Column(Boolean, default=False)
    total_debit = Column(Float, default=0)
    total_credit = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    lines = relationship("JournalLine", back_populates="journal", cascade="all, delete-orphan")


class JournalLine(Base):
    __tablename__ = "journal_lines"
    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    description = Column(String)
    debit = Column(Float, default=0)
    credit = Column(Float, default=0)
    journal = relationship("Journal", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")

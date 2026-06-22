#!/usr/bin/env python3
"""Run this once after first docker-compose up to create the admin user."""
import sys, os
sys.path.insert(0, '/app')

from app.core.database import Base, engine, SessionLocal
from app.modules.auth.models import User, UserRole
from app.modules.crm.models import Contact, Lead, Deal
from app.modules.inventory.models import Product, Order, OrderItem
from app.modules.accounting.models import Invoice, InvoiceItem, Transaction
from app.modules.hr.models import Employee, LeaveRequest, Payroll
from app.core.security import get_password_hash
from datetime import date

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(User).filter(User.email == 'admin@knooz.com').first():
    db.add(User(
        email='admin@knooz.com',
        full_name='Admin User',
        hashed_password=get_password_hash('admin123'),
        role=UserRole.admin,
        is_active=True,
    ))
    db.commit()
    print('✅ Admin user created: admin@knooz.com / admin123')
else:
    print('ℹ️  Admin user already exists')

db.close()
print('✅ Database ready')

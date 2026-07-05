from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

PUBLIC_TENANTS_TABLE = """
CREATE TABLE IF NOT EXISTS public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL UNIQUE,
    domain VARCHAR(100) UNIQUE,
    plan VARCHAR(20) NOT NULL DEFAULT 'starter',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

ENUM_DEFINITIONS = """
DO $$ BEGIN CREATE TYPE user_role AS ENUM ('admin','manager','employee','accountant'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE lead_status AS ENUM ('new','contacted','qualified','lost'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE deal_stage AS ENUM ('prospecting','proposal','negotiation','closed_won','closed_lost'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE invoice_status AS ENUM ('draft','sent','paid','overdue','cancelled'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE transaction_type AS ENUM ('income','expense'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE journal_type AS ENUM ('sale','purchase','bank','cash','general'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE employment_type AS ENUM ('full_time','part_time','contract'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE leave_type AS ENUM ('annual','sick','unpaid','maternity'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE leave_status AS ENUM ('pending','approved','rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE order_status AS ENUM ('pending','confirmed','shipped','delivered','cancelled'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
"""

TABLE_DEFINITIONS = """
CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email VARCHAR NOT NULL UNIQUE, full_name VARCHAR NOT NULL, hashed_password VARCHAR NOT NULL, role user_role NOT NULL DEFAULT 'employee', is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE TABLE IF NOT EXISTS contacts (id SERIAL PRIMARY KEY, first_name VARCHAR NOT NULL, last_name VARCHAR NOT NULL, email VARCHAR UNIQUE, phone VARCHAR, company VARCHAR, position VARCHAR, notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ);
CREATE INDEX IF NOT EXISTS ix_contacts_email ON contacts (email);
CREATE TABLE IF NOT EXISTS leads (id SERIAL PRIMARY KEY, title VARCHAR NOT NULL, contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL, status lead_status NOT NULL DEFAULT 'new', source VARCHAR, estimated_value FLOAT NOT NULL DEFAULT 0, notes TEXT, assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS deals (id SERIAL PRIMARY KEY, title VARCHAR NOT NULL, contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL, stage deal_stage NOT NULL DEFAULT 'prospecting', value FLOAT NOT NULL DEFAULT 0, close_date TIMESTAMPTZ, notes TEXT, assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS invoices (id SERIAL PRIMARY KEY, invoice_number VARCHAR UNIQUE, client_name VARCHAR NOT NULL, client_email VARCHAR, status invoice_status NOT NULL DEFAULT 'draft', issue_date DATE NOT NULL, due_date DATE NOT NULL, subtotal FLOAT NOT NULL DEFAULT 0, tax_rate FLOAT NOT NULL DEFAULT 15, tax_amount FLOAT NOT NULL DEFAULT 0, total FLOAT NOT NULL DEFAULT 0, notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_invoices_number ON invoices (invoice_number);
CREATE TABLE IF NOT EXISTS invoice_items (id SERIAL PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE, description VARCHAR NOT NULL, quantity FLOAT NOT NULL DEFAULT 1, unit_price FLOAT NOT NULL, total FLOAT NOT NULL);
CREATE TABLE IF NOT EXISTS transactions (id SERIAL PRIMARY KEY, type transaction_type NOT NULL, amount FLOAT NOT NULL, description VARCHAR NOT NULL, category VARCHAR, reference VARCHAR, date DATE NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS accounts (id SERIAL PRIMARY KEY, code VARCHAR NOT NULL UNIQUE, name VARCHAR NOT NULL, name_ar VARCHAR, account_type VARCHAR NOT NULL, balance FLOAT NOT NULL DEFAULT 0, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_accounts_code ON accounts (code);
CREATE TABLE IF NOT EXISTS journals (id SERIAL PRIMARY KEY, journal_number VARCHAR UNIQUE, journal_type journal_type NOT NULL DEFAULT 'general', date DATE NOT NULL, description VARCHAR NOT NULL, reference VARCHAR, is_posted BOOLEAN NOT NULL DEFAULT FALSE, total_debit FLOAT NOT NULL DEFAULT 0, total_credit FLOAT NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_journals_number ON journals (journal_number);
CREATE TABLE IF NOT EXISTS journal_lines (id SERIAL PRIMARY KEY, journal_id INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE, account_id INTEGER NOT NULL REFERENCES accounts(id), description VARCHAR, debit FLOAT NOT NULL DEFAULT 0, credit FLOAT NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS employees (id SERIAL PRIMARY KEY, employee_id VARCHAR UNIQUE, first_name VARCHAR NOT NULL, last_name VARCHAR NOT NULL, email VARCHAR UNIQUE, phone VARCHAR, department VARCHAR, position VARCHAR, employment_type employment_type NOT NULL DEFAULT 'full_time', salary FLOAT NOT NULL DEFAULT 0, hire_date DATE NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_employees_employee_id ON employees (employee_id);
CREATE INDEX IF NOT EXISTS ix_employees_email ON employees (email);
CREATE TABLE IF NOT EXISTS leave_requests (id SERIAL PRIMARY KEY, employee_id INTEGER NOT NULL, leave_type leave_type NOT NULL, start_date DATE NOT NULL, end_date DATE NOT NULL, days INTEGER NOT NULL, reason TEXT, status leave_status NOT NULL DEFAULT 'pending', created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS payroll (id SERIAL PRIMARY KEY, employee_id INTEGER NOT NULL, period_month INTEGER NOT NULL, period_year INTEGER NOT NULL, base_salary FLOAT NOT NULL, allowances FLOAT NOT NULL DEFAULT 0, deductions FLOAT NOT NULL DEFAULT 0, net_salary FLOAT NOT NULL, status VARCHAR NOT NULL DEFAULT 'pending', created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, name VARCHAR NOT NULL, sku VARCHAR UNIQUE, description TEXT, price FLOAT NOT NULL DEFAULT 0, cost FLOAT NOT NULL DEFAULT 0, stock_qty INTEGER NOT NULL DEFAULT 0, reorder_level INTEGER NOT NULL DEFAULT 10, category VARCHAR, unit VARCHAR NOT NULL DEFAULT 'pcs', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ);
CREATE INDEX IF NOT EXISTS ix_products_sku ON products (sku);
CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, order_number VARCHAR UNIQUE, customer_name VARCHAR NOT NULL, customer_email VARCHAR, status order_status NOT NULL DEFAULT 'pending', total_amount FLOAT NOT NULL DEFAULT 0, notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ);
CREATE INDEX IF NOT EXISTS ix_orders_order_number ON orders (order_number);
CREATE TABLE IF NOT EXISTS order_items (id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE, product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL, unit_price FLOAT NOT NULL, total FLOAT NOT NULL);
"""

DEFAULT_ACCOUNTS_SQL = """
INSERT INTO accounts (code, name, name_ar, account_type, balance) VALUES
('1000','Cash','نقد','asset',0),
('1100','Accounts Receivable','حسابات القبض','asset',0),
('1200','Inventory','المخزون','asset',0),
('2000','Accounts Payable','حسابات الدفع','liability',0),
('2100','Accrued Liabilities','الالتزامات المستحقة','liability',0),
('3000','Owner Equity','حقوق الملكية','equity',0),
('4000','Sales Revenue','إيرادات المبيعات','income',0),
('4100','Other Income','إيرادات أخرى','income',0),
('5000','Cost of Goods Sold','تكلفة البضاعة المباعة','expense',0),
('5100','Salaries Expense','مصروف الرواتب','expense',0),
('5200','Rent Expense','مصروف الإيجار','expense',0),
('5300','Utilities Expense','مصروف المرافق','expense',0),
('5400','General & Admin','مصروفات عمومية وإدارية','expense',0)
ON CONFLICT (code) DO NOTHING;
"""


def provision_tenant(db: Session, slug: str, admin_email: str = None,
                     admin_name: str = None, admin_hashed_password: str = None) -> None:
    logger.info(f"Provisioning tenant: {slug}")
    try:
        db.execute(text(PUBLIC_TENANTS_TABLE))
        db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{slug}"'))
        db.execute(text(f'SET search_path TO "{slug}", public'))
        db.execute(text(ENUM_DEFINITIONS))
        db.execute(text(TABLE_DEFINITIONS))
        db.execute(text(DEFAULT_ACCOUNTS_SQL))
        if admin_email and admin_name and admin_hashed_password:
            db.execute(text("""
                INSERT INTO users (email, full_name, hashed_password, role)
                VALUES (:email, :name, :password, 'admin')
                ON CONFLICT (email) DO NOTHING
            """), {"email": admin_email, "name": admin_name, "password": admin_hashed_password})
        db.commit()
        logger.info(f"Tenant '{slug}' provisioned successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to provision tenant '{slug}': {e}")
        raise


def deprovision_tenant(db: Session, slug: str) -> None:
    logger.warning(f"Deprovisioning tenant: {slug}")
    try:
        db.execute(text(f'DROP SCHEMA IF EXISTS "{slug}" CASCADE'))
        db.execute(text("DELETE FROM public.tenants WHERE slug = :slug"), {"slug": slug})
        db.commit()
    except Exception as e:
        db.rollback()
        raise


def tenant_exists(db: Session, slug: str) -> bool:
    result = db.execute(text(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :slug"
    ), {"slug": slug})
    return result.fetchone() is not None


def list_tenants(db: Session) -> list:
    result = db.execute(text(
        "SELECT id, name, slug, domain, plan, is_active, created_at "
        "FROM public.tenants ORDER BY created_at DESC"
    ))
    return [dict(row._mapping) for row in result.fetchall()]

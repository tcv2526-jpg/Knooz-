from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.inventory.models import Product, Order, OrderItem, OrderStatus
import random, string

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def gen_order_number():
    return "ORD-" + "".join(random.choices(string.digits, k=6))

def gen_req_number():
    return "REQ-" + "".join(random.choices(string.digits, k=5))


class ProductCreate(BaseModel):
    name: str
    sku: str
    description: Optional[str] = None
    price: float
    cost: float = 0
    stock_qty: int = 0
    reorder_level: int = 10
    category: Optional[str] = None
    unit: str = "pcs"

class ProductOut(ProductCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class OrderItemIn(BaseModel):
    product_id: int
    quantity: int
    unit_price: float

class OrderCreate(BaseModel):
    customer_name: str
    customer_email: Optional[str] = None
    notes: Optional[str] = None
    items: List[OrderItemIn]

class OrderItemOut(BaseModel):
    id: int; product_id: int; quantity: int; unit_price: float; total: float
    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int; order_number: str; customer_name: str
    customer_email: Optional[str]; status: OrderStatus
    total_amount: float; notes: Optional[str]
    items: List[OrderItemOut]; created_at: datetime
    class Config:
        from_attributes = True

class StockAdjustment(BaseModel):
    product_id: int
    adjustment_qty: int
    reason: str
    type: str = "in"

class RequisitionCreate(BaseModel):
    product_id: int
    requested_qty: int
    preferred_vendor: Optional[str] = None
    expected_price: Optional[float] = None
    notes: Optional[str] = None
    urgency: str = "normal"


@router.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Product).order_by(Product.name).all()

@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Product).filter(Product.sku == product.sku).first():
        raise HTTPException(400, "SKU already exists")
    obj = Product(**product.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Product).filter(Product.id == product_id).first()
    if not obj: raise HTTPException(404, "Product not found")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Product).filter(Product.id == product_id).first()
    if not obj: raise HTTPException(404, "Product not found")
    db.delete(obj); db.commit()


@router.get("/orders", response_model=List[OrderOut])
def list_orders(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Order).order_by(Order.created_at.desc()).all()

@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    total = sum(i.quantity * i.unit_price for i in order.items)
    obj = Order(
        order_number=gen_order_number(),
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        notes=order.notes,
        total_amount=total,
    )
    db.add(obj); db.flush()
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock_qty = max(0, product.stock_qty - item.quantity)
        db.add(OrderItem(
            order_id=obj.id, product_id=item.product_id,
            quantity=item.quantity, unit_price=item.unit_price,
            total=item.quantity * item.unit_price,
        ))
    db.commit(); db.refresh(obj)
    return obj

@router.put("/orders/{order_id}/status")
def update_order_status(order_id: int, status: OrderStatus, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Order).filter(Order.id == order_id).first()
    if not obj: raise HTTPException(404, "Order not found")
    obj.status = status; db.commit()
    return {"id": obj.id, "status": obj.status}


@router.post("/stock-adjustment")
def stock_adjustment(adj: StockAdjustment, db: Session = Depends(get_db), _=Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == adj.product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    old_qty = product.stock_qty
    if adj.type == "in":
        product.stock_qty += adj.adjustment_qty
    else:
        product.stock_qty = max(0, product.stock_qty - adj.adjustment_qty)
    db.commit()
    db.refresh(product)
    return {
        "product_id": product.id,
        "product_name": product.name,
        "old_stock": old_qty,
        "adjustment": adj.adjustment_qty,
        "type": adj.type,
        "new_stock": product.stock_qty,
        "reason": adj.reason
    }


@router.get("/stock-card/{product_id}")
def stock_card(
    product_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")

    query = db.query(OrderItem).filter(
        OrderItem.product_id == product_id
    ).join(Order)

    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to + " 23:59:59")

    items = query.order_by(Order.created_at).all()

    total_sold_in_period = sum(i.quantity for i in items)
    opening_stock = product.stock_qty + total_sold_in_period

    movements = []
    running = opening_stock
    for item in items:
        running -= item.quantity
        movements.append({
            "date": str(item.order.created_at.date()),
            "reference": item.order.order_number,
            "customer": item.order.customer_name,
            "type": "out",
            "qty_in": 0,
            "qty_out": item.quantity,
            "unit_price": item.unit_price,
            "total": item.total,
            "running_balance": running,
            "status": item.order.status,
        })

    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "category": product.category or "",
            "unit": product.unit,
            "price": product.price,
            "cost": product.cost,
            "current_stock": product.stock_qty,
            "reorder_level": product.reorder_level,
        },
        "date_from": date_from,
        "date_to": date_to,
        "opening_stock": opening_stock,
        "movements": movements,
        "total_in": sum(m["qty_in"] for m in movements),
        "total_out": sum(m["qty_out"] for m in movements),
        "closing_stock": product.stock_qty,
    }


def ensure_requisitions_table(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS purchase_requisitions (
            id SERIAL PRIMARY KEY,
            req_number VARCHAR UNIQUE NOT NULL,
            product_id INTEGER NOT NULL,
            product_name VARCHAR NOT NULL,
            product_sku VARCHAR,
            product_unit VARCHAR DEFAULT 'pcs',
            current_stock INTEGER DEFAULT 0,
            reorder_level INTEGER DEFAULT 0,
            requested_qty INTEGER NOT NULL,
            preferred_vendor VARCHAR,
            expected_price FLOAT,
            notes TEXT,
            urgency VARCHAR DEFAULT 'normal',
            status VARCHAR DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    db.commit()

@router.get("/requisitions")
def list_requisitions(db: Session = Depends(get_db), _=Depends(get_current_user)):
    ensure_requisitions_table(db)
    result = db.execute(text(
        "SELECT id, req_number, product_id, product_name, product_sku, product_unit, "
        "current_stock, reorder_level, requested_qty, preferred_vendor, expected_price, "
        "notes, urgency, status, created_at FROM purchase_requisitions ORDER BY created_at DESC"
    )).fetchall()
    keys = ["id","req_number","product_id","product_name","product_sku","product_unit",
            "current_stock","reorder_level","requested_qty","preferred_vendor","expected_price",
            "notes","urgency","status","created_at"]
    return [dict(zip(keys, row)) for row in result]

@router.post("/requisitions", status_code=201)
def create_requisition(req: RequisitionCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    ensure_requisitions_table(db)
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    req_number = gen_req_number()
    db.execute(text("""
        INSERT INTO purchase_requisitions
        (req_number, product_id, product_name, product_sku, product_unit,
         current_stock, reorder_level, requested_qty, preferred_vendor,
         expected_price, notes, urgency, status)
        VALUES (:rn, :pid, :pn, :ps, :pu, :cs, :rl, :qty, :pv, :ep, :notes, :urg, 'draft')
    """), {
        "rn": req_number, "pid": product.id, "pn": product.name,
        "ps": product.sku, "pu": product.unit,
        "cs": product.stock_qty, "rl": product.reorder_level,
        "qty": req.requested_qty, "pv": req.preferred_vendor,
        "ep": req.expected_price, "notes": req.notes, "urg": req.urgency
    })
    db.commit()
    return {
        "req_number": req_number, "status": "draft",
        "product_name": product.name, "product_sku": product.sku,
        "current_stock": product.stock_qty, "requested_qty": req.requested_qty
    }

@router.put("/requisitions/{req_id}/status")
def update_requisition_status(req_id: int, status: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    ensure_requisitions_table(db)
    db.execute(text("UPDATE purchase_requisitions SET status=:s WHERE id=:id"), {"s": status, "id": req_id})
    db.commit()
    return {"id": req_id, "status": status}

@router.delete("/requisitions/{req_id}", status_code=204)
def delete_requisition(req_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    ensure_requisitions_table(db)
    db.execute(text("DELETE FROM purchase_requisitions WHERE id=:id"), {"id": req_id})
    db.commit()


@router.get("/stats")
def inventory_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return {
        "total_products": db.query(Product).count(),
        "total_orders": db.query(Order).count(),
        "low_stock_count": db.query(Product).filter(Product.stock_qty <= Product.reorder_level).count(),
        "total_stock_value": db.query(func.sum(Product.stock_qty * Product.cost)).scalar() or 0,
        "pending_orders": db.query(Order).filter(Order.status == OrderStatus.pending).count(),
    }

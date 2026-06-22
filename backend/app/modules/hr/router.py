from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.hr.models import Employee, LeaveRequest, Payroll, EmploymentType, LeaveType, LeaveStatus
import random, string

router = APIRouter(prefix="/api/hr", tags=["hr"])


def gen_employee_id():
    return "EMP-" + "".join(random.choices(string.digits, k=4))


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    employment_type: EmploymentType = EmploymentType.full_time
    salary: float = 0
    hire_date: date

class EmployeeOut(EmployeeCreate):
    id: int
    employee_id: str
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None

class LeaveOut(LeaveCreate):
    id: int
    days: int
    status: LeaveStatus
    created_at: datetime
    class Config:
        from_attributes = True

class PayrollCreate(BaseModel):
    employee_id: int
    period_month: int
    period_year: int
    allowances: float = 0
    deductions: float = 0

class PayrollOut(PayrollCreate):
    id: int
    base_salary: float
    net_salary: float
    status: str
    created_at: datetime
    class Config:
        from_attributes = True


# ── Employees ─────────────────────────────────────────────
@router.get("/employees", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Employee).order_by(Employee.first_name).all()

@router.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(emp: EmployeeCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = Employee(**emp.model_dump(), employee_id=gen_employee_id())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, data: EmployeeCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Employee).filter(Employee.id == employee_id).first()
    if not obj: raise HTTPException(404, "Employee not found")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(Employee).filter(Employee.id == employee_id).first()
    if not obj: raise HTTPException(404, "Employee not found")
    db.delete(obj); db.commit()

# ── Leave Requests ────────────────────────────────────────
@router.get("/leaves", response_model=List[LeaveOut])
def list_leaves(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(LeaveRequest).order_by(LeaveRequest.created_at.desc()).all()

@router.post("/leaves", response_model=LeaveOut, status_code=201)
def create_leave(leave: LeaveCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    days = (leave.end_date - leave.start_date).days + 1
    obj = LeaveRequest(**leave.model_dump(), days=days)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/leaves/{leave_id}/status")
def update_leave_status(leave_id: int, status: LeaveStatus, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not obj: raise HTTPException(404, "Leave request not found")
    obj.status = status
    db.commit()
    return {"id": obj.id, "status": obj.status}

# ── Payroll ───────────────────────────────────────────────
@router.get("/payroll", response_model=List[PayrollOut])
def list_payroll(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Payroll).order_by(Payroll.created_at.desc()).all()

@router.post("/payroll", response_model=PayrollOut, status_code=201)
def create_payroll(p: PayrollCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == p.employee_id).first()
    if not emp: raise HTTPException(404, "Employee not found")
    net = emp.salary + p.allowances - p.deductions
    obj = Payroll(**p.model_dump(), base_salary=emp.salary, net_salary=net)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.get("/stats")
def hr_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import func
    return {
        "total_employees": db.query(Employee).filter(Employee.is_active == True).count(),
        "pending_leaves": db.query(LeaveRequest).filter(LeaveRequest.status == LeaveStatus.pending).count(),
        "total_payroll": db.query(func.sum(Payroll.net_salary)).scalar() or 0,
        "departments": db.query(Employee.department, func.count()).group_by(Employee.department).all(),
    }

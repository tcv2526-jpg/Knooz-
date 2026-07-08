from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import UserCreate, UserOut, Token, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # Resolve tenant from header
    from fastapi import Request
    tenant_slug = None

    # Try to find user across tenants if no slug provided
    # First check if tenant_slug is in the request body
    slug = getattr(credentials, "tenant_slug", None)

    if slug:
        # Set schema to tenant
        db.execute(text(f'SET search_path TO "{slug}", public'))
        tenant_slug = slug

    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    token = create_access_token({
        "sub": str(user.id),
        "tenant_slug": tenant_slug or "public",
        "role": user.role.value,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_slug": tenant_slug or "public",
        "user": user,
    }


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(User).all()

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginInput, TokenOut
from app.schemas.user import UserCreate, UserOut


router = APIRouter(prefix="/auth", tags=["auth"])


def _build_token(user: User) -> TokenOut:
    token = create_access_token(subject=user.id)
    return TokenOut(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni hesap oluştur",
)
def register(payload: UserCreate, db: DbSession) -> TokenOut:
    normalized_email = payload.email.lower().strip()

    existing = db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta zaten kayıtlı.",
        )

    user = User(
        email=normalized_email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _build_token(user)


@router.post(
    "/login",
    response_model=TokenOut,
    summary="E-posta ve şifre ile giriş",
)
def login(payload: LoginInput, db: DbSession) -> TokenOut:
    normalized_email = payload.email.lower().strip()
    user = db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    ).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız pasif durumda.",
        )

    return _build_token(user)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Mevcut kullanıcının profili",
)
def me(current_user: CurrentUser) -> User:
    return current_user

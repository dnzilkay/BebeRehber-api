from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserPlan, UserRole


DEMO_PASSWORD = "demo1234"

DEMO_USERS: list[dict[str, object]] = [
    {
        "email": "deniz@example.com",
        "name": "Deniz",
        "plan": UserPlan.PREMIUM,
        "role": UserRole.USER,
    },
    {
        "email": "free@example.com",
        "name": "Ücretsiz Kullanıcı",
        "plan": UserPlan.FREE,
        "role": UserRole.USER,
    },
    {
        "email": "admin@example.com",
        "name": "Yönetici",
        "plan": UserPlan.PREMIUM,
        "role": UserRole.ADMIN,
    },
]


def seed_demo_users(db: Session) -> int:
    """Idempotently insert demo users. Returns number of newly created rows."""
    created = 0
    password_hash = hash_password(DEMO_PASSWORD)

    for entry in DEMO_USERS:
        email = str(entry["email"])
        existing = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            continue

        user = User(
            email=email,
            name=str(entry["name"]),
            password_hash=password_hash,
            plan=entry["plan"],  # type: ignore[arg-type]
            role=entry["role"],  # type: ignore[arg-type]
        )
        db.add(user)
        created += 1

    if created:
        db.commit()
    return created

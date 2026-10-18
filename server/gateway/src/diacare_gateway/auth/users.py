"""Creating users (used by the register endpoint and the command-line tool)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from diacare_gateway.auth.passwords import hash_password
from diacare_gateway.db.models import ROLES, AppUser
from diacare_shared.errors import AppError

EMAIL_TAKEN = "EMAIL_TAKEN"


def find_user_by_email(session: Session, email: str) -> AppUser | None:
    return session.scalar(select(AppUser).where(func.lower(AppUser.email) == email.lower()))


def create_user(
    session: Session,
    *,
    email: str,
    password: str,
    display_name: str | None = None,
    role: str = "patient",
    is_demo: bool = False,
) -> AppUser:
    """Add a user to the session (the caller commits). Raises 409 if the e-mail is in use."""
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    email = email.strip().lower()
    if find_user_by_email(session, email) is not None:
        raise AppError(409, EMAIL_TAKEN, "An account with this e-mail already exists.")
    user = AppUser(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        is_demo=is_demo,
    )
    session.add(user)
    session.flush()
    return user

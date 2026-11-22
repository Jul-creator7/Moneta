from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .banking_defaults import provision_accounts
from .models import User
from .schemas import Credentials, Registration

hasher = PasswordHasher()
dummy_hash = hasher.hash("unused-login-placeholder")


class DuplicateUser(Exception):
    pass


def register(db: Session, data: Registration) -> User:
    user = User(
        email=data.email.lower(),
        username=data.username.lower(),
        password_hash=hasher.hash(data.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.flush()
        provision_accounts(db, user.id)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateUser from error
    db.refresh(user)
    return user


def authenticate(db: Session, data: Credentials) -> User | None:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    try:
        hasher.verify(user.password_hash if user else dummy_hash, data.password.get_secret_value())
    except VerifyMismatchError:
        return None
    return user


def issue_token(user: User, secret: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=30)},
        secret,
        algorithm="HS256",
    )


def read_subject(token: str, secret: str) -> int:
    claims = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "iat", "sub"]})
    return int(claims["sub"])

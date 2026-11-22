import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import auth_service
from .models import User
from .schemas import Credentials, PublicUser, Registration, Token

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    with request.app.state.sessions() as session:
        yield session


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise unauthorized("Sign in to continue")
    try:
        user_id = auth_service.read_subject(credentials.credentials, request.app.state.settings.jwt_secret)
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized("Session expired or invalid") from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized("Session expired or invalid")
    return user


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/auth/register", response_model=PublicUser, status_code=201)
def register(data: Registration, db: Session = Depends(get_db)):
    try:
        return auth_service.register(db, data)
    except auth_service.DuplicateUser:
        raise HTTPException(409, "Email or username is already registered") from None


@router.post("/auth/login", response_model=Token)
def login(data: Credentials, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, data)
    if user is None:
        raise unauthorized("Invalid email or password")
    return Token(access_token=auth_service.issue_token(user, request.app.state.settings.jwt_secret))


@router.get("/users/me", response_model=PublicUser)
def me(user: User = Depends(current_user)):
    return user

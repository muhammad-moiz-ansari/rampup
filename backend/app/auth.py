from datetime import timedelta
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db
from app.errors import AppError
from app.models import User, now

passwords = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        if not credentials or len(get_settings().jwt_secret) < 32:
            raise ValueError()
        payload = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            audience="rampup",
            options={"require": ["exp", "sub", "iat"]},
        )
        user = db.get(User, payload["sub"])
        if not user:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError):
        raise AppError(
            401, "UNAUTHORIZED", "Sign in with a valid access token."
        ) from None


def public_user(user):
    return {"id": user.id, "name": user.name, "role": user.role}


def issue_token(user):
    settings = get_settings()
    if len(settings.jwt_secret) < 32:
        raise AppError(
            503, "AUTH_NOT_CONFIGURED", "Server authentication is not configured.", True
        )
    expires = now() + timedelta(minutes=settings.access_token_ttl_minutes)
    token = jwt.encode(
        {"sub": user.id, "iat": now(), "exp": expires, "aud": "rampup"},
        settings.jwt_secret,
        algorithm="HS256",
    )
    return {
        "access_token": token,
        "expires_at": expires,
        "token_type": "bearer",
        "user": public_user(user),
    }

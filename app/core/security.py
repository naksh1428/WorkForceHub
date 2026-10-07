"""Helpers for keeping passwords safe and for login tokens."""
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Scramble a password so it can be stored safely."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Check if a password matches the scrambled one we stored."""
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """Make a login token for this user. It stops working after a set time."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Read the username from a login token.

    Gives back None if the token is fake, broken or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None

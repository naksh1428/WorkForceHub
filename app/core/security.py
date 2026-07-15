"""Password hashing and JWT token helpers."""
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password for storage.

    Args:
        password: The plain-text password.

    Returns:
        A salted PBKDF2-SHA256 hash suitable for storing in the database.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain-text password against a stored hash.

    Args:
        plain: The plain-text password supplied by the user.
        hashed: The hash previously produced by `hash_password`.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """Create a signed JWT access token for a given subject.

    Args:
        subject: The value to embed in the token's `sub` claim (the username).

    Returns:
        An encoded JWT string, valid for `settings.ACCESS_TOKEN_EXPIRE_MINUTES`.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Decode and validate a JWT access token.

    Args:
        token: The encoded JWT string presented by the client.

    Returns:
        The subject (username) if the token is valid and unexpired, else None.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None

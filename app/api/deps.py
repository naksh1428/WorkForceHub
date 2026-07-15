"""Shared FastAPI dependencies for the API routers."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.models import User

# tokenUrl points Swagger UI's "Authorize" button at the login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the request's bearer token.

    Args:
        token: JWT bearer token extracted from the `Authorization` header.
        db: Database session, injected.

    Returns:
        The `User` row matching the token's subject claim.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing, invalid,
            expired, or no longer matches an existing user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = decode_access_token(token)
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user
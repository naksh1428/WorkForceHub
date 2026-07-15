"""Authentication endpoints: register and login."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import Token, UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
    """Create a new user account and return a JWT for immediate use.

    Args:
        payload: Desired username and plain-text password. The password is
            hashed with PBKDF2-SHA256 before being stored.
        db: Database session, injected.

    Returns:
        A bearer token for the newly created user.

    Raises:
        HTTPException: 409 Conflict if the username is already taken.
    """
    user = User(username=payload.username, hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already registered"
        ) from exc
    db.refresh(user)
    return Token(access_token=create_access_token(user.username))


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate a user via the OAuth2 password flow and return a JWT.

    Args:
        form_data: OAuth2 form data containing `username` and `password`
            (submitted as `application/x-www-form-urlencoded`, not JSON).
        db: Database session, injected.

    Returns:
        A bearer token for the authenticated user.

    Raises:
        HTTPException: 401 Unauthorized if the username doesn't exist or
            the password is incorrect.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.username))
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.security import decode_access_token
from backend.models.models import User

# OAuth2 scheme: Tells FastAPI to look for a 'Bearer <token>' in the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI Security Dependency:
    1. Extracts JWT token from the Authorization header.
    2. Decodes and verifies the signature using security.py.
    3. Queries Supabase to fetch the current active User.
    4. Raises HTTP 401 Unauthorized if token is invalid or user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user

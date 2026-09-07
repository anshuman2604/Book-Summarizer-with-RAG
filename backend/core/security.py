from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from backend.core.config import settings

# 1. CryptContext configured with bcrypt algorithm for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.
    Never store plain text passwords in the database!
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against the stored bcrypt hash.
    Returns True if valid, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a secure JSON Web Token (JWT) containing the user's ID as the 'sub' claim.
    Signed using the SECRET_KEY and HS256 algorithm from settings.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),  # User ID
        "exp": expire         # Expiration timestamp
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    """
    Decodes and validates a JWT token.
    Returns the user ID (subject) if valid and unexpired, None if invalid or forged.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None

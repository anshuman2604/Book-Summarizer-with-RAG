import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.models import User
from backend.core.security import hash_password, verify_password, create_access_token
from backend.schemas.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse
)
from backend.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user"
)
def register(
    user_in: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registers a new user:
    1. Checks if email is already taken.
    2. Hashes password using bcrypt.
    3. Saves new User record in Supabase.
    4. Returns HTTP 201 Created with safe user profile (no password).
    """
    # Check for existing user with same email
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Create new user with hashed password
    new_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User registered successfully: {new_user.email}")
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in and obtain JWT access token"
)
def login(
    login_data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Logs in a user:
    1. Looks up user by email in Supabase.
    2. Verifies entered password against bcrypt hash.
    3. Generates and returns a signed 24-hour JWT access token.
    """
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Generate signed JWT token containing user.id
    access_token = create_access_token(subject=user.id)

    logger.info(f"User logged in successfully: {user.email}")
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current logged-in user profile"
)
def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Returns the authenticated user's profile.
    Protected endpoint: requires valid JWT Bearer token in Authorization header.
    """
    return current_user

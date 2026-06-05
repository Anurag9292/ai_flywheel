"""Authentication endpoints — login, token refresh, user info."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ai_flywheel.core.auth import User, create_access_token, get_current_user
from ai_flywheel.core.config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    """Simple email-based login for development."""
    email: str
    password: str = ""  # In dev mode, any password works


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    ventures: list[str]


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Login and get an access token.
    
    In development mode, any email/password combination works.
    In production, this would validate against a user store.
    """
    if settings.is_production:
        # TODO: Implement real user validation
        raise HTTPException(status_code=501, detail="Production auth not configured")
    
    # Development mode — create token for any user
    user_id = f"user_{request.email.split('@')[0]}"
    token = create_access_token(
        user_id=user_id,
        email=request.email,
        ventures=["*"],  # Dev users have access to all ventures
    )
    
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_hours * 3600,
        user={"id": user_id, "email": request.email, "ventures": ["*"]},
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Get current user info."""
    return UserResponse(id=user.id, email=user.email, ventures=user.ventures)

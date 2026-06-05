"""Authentication — simple JWT-based auth for the platform.

In development mode, auth is optional (requests without tokens are allowed).
In production, all API requests must have a valid Bearer token.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from ai_flywheel.core.config import settings

logger = structlog.get_logger()

# Security scheme — optional in dev mode
security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user identifier
    exp: datetime
    ventures: list[str] = []  # venture IDs this user can access


class User(BaseModel):
    """Authenticated user context."""
    id: str
    email: str = ""
    ventures: list[str] = []


# Default dev user for when auth is skipped
DEV_USER = User(id="dev-user", email="dev@flywheel.local", ventures=["*"])


def create_access_token(user_id: str, email: str = "", ventures: list[str] | None = None) -> str:
    """Create a JWT access token."""
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expiration_hours)
    payload = {
        "sub": user_id,
        "email": email,
        "ventures": ventures or [],
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> User:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return User(
            id=payload["sub"],
            email=payload.get("email", ""),
            ventures=payload.get("ventures", []),
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Get the current authenticated user.
    
    In development mode: returns dev user if no token provided.
    In production mode: requires valid JWT token.
    """
    if credentials and credentials.credentials:
        return verify_token(credentials.credentials)
    
    # In dev mode, allow unauthenticated access
    if settings.is_development:
        return DEV_USER
    
    raise HTTPException(status_code=401, detail="Authentication required")

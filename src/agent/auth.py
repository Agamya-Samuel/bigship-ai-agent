from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from agent.config import settings

ALGORITHM = "HS256"
JWT_SECRET = settings.jwt_secret
JWT_EXPIRY_MINUTES = settings.jwt_expiry_minutes

security = HTTPBearer()


def create_access_token(account_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    return jwt.encode({"sub": account_id, "exp": expire}, JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    payload = decode_access_token(token)
    account_id = payload.get("sub")
    if account_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return str(account_id)


def get_current_account_optional(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except HTTPException:
        return None
    account_id = payload.get("sub")
    return str(account_id) if account_id else None

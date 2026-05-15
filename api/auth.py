from datetime import datetime, timedelta, UTC
from typing import Annotated
from uuid import UUID as PyUUID

from fastapi import APIRouter, Depends, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.database import get_db
from core.dependencies import CurrentSession
from core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_refresh_token,
)
from models.session import Session
from models.user import AuthProvider, User
from schemas.schemas import GoogleAuthRequest, RefreshTokenRequest, TokenResponse

router = APIRouter()

allowed_audiences = {settings.google_web_client_id}


def _issue_tokens(user: User, session: Session) -> TokenResponse:
    access_token = create_access_token({"sub": str(user.id), "session_id": str(session.id)})
    refresh_token = create_refresh_token({"sub": str(user.id), "session_id": str(session.id)})
    session.refresh_token_hash = hash_refresh_token(refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/google", response_model=TokenResponse)
async def google_sign_in(
    data: GoogleAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        idinfo = id_token.verify_oauth2_token(data.id_token, google_requests.Request())
    except ValueError as e:
        raise HTTPException(401, f"Invalid Google token: {e}")

    if idinfo.get("aud") not in allowed_audiences:
        raise HTTPException(401, "Invalid audience")

    provider_user_id = idinfo["sub"]
    email = idinfo.get("email")
    name = idinfo.get("given_name")
    surname = idinfo.get("family_name")

    result = await db.execute(
        select(User).where(
            User.provider_user_id == provider_user_id,
            User.provider == AuthProvider.google,
        )
    )
    user = result.scalars().first()

    if not user:
        user = User(
            email=email,
            name=name,
            surname=surname,
            provider=AuthProvider.google,
            provider_user_id=provider_user_id,
            last_login_at=datetime.now(UTC),
        )
        db.add(user)
        await db.flush()
    else:
        user.last_login_at = datetime.now(UTC)

    session = Session(
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    await db.flush()

    tokens = _issue_tokens(user, session)
    await db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    payload = verify_refresh_token(data.refresh_token)
    if payload is None:
        raise HTTPException(401, "Invalid refresh token")

    try:
        user_id = PyUUID(payload["sub"])
        session_id = PyUUID(payload["session_id"])
    except (KeyError, ValueError):
        raise HTTPException(401, "Invalid refresh token")

    session = (await db.execute(select(Session).where(Session.id == session_id))).scalars().first()
    if not session or session.revoked_at is not None:
        raise HTTPException(401, "Session revoked")
    if session.expires_at < datetime.now(UTC):
        raise HTTPException(401, "Session expired")
    if session.refresh_token_hash != hash_refresh_token(data.refresh_token):
        raise HTTPException(401, "Refresh token mismatch")

    user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
    if not user:
        raise HTTPException(401, "User not found")

    tokens = _issue_tokens(user, session)
    await db.commit()
    return tokens


@router.post("/logout")
async def logout(
    session: CurrentSession,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session.revoked_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}

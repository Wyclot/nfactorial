from typing import Annotated
from uuid import UUID as PyUUID
from models.session import Session
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from core.database import get_db
from core.security import verify_access_token
from models.user import User

from typing import Annotated

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime,UTC

from config import settings


bearer_scheme = HTTPBearer()

async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
        db:Annotated[AsyncSession,Depends(get_db)]
)->User:
    token = credentials.credentials

    payload = verify_access_token(token)

    if payload is None:
        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Invalid or expired token",

        )

    user_id_str = payload.get("sub")

    if not user_id_str:
        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Invalid token payload",

        )

    try:

        user_id = PyUUID(user_id_str)

    except ValueError:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Invalid user id in token",

        )

    result = await db.execute(

        select(User)

        .where(User.id == user_id)

        .options(selectinload(User.roles))

    )

    user = result.scalars().first()



    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_banned:
        raise HTTPException(403, "Account is banned")

    session_id_str = payload.get("session_id")

    try:
        session_id = PyUUID(session_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.revoked_at.is_(None)
        )
    )
    db_session = session_result.scalars().first()

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked"
        )
    return user

async def get_current_session(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],db:Annotated[AsyncSession,Depends(get_db)]):
    token = credentials.credentials

    payload = verify_access_token(token)

    if payload is None:
        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Invalid or expired token",

        )

    session_id_str = payload.get("session_id")

    if not session_id_str:
        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Invalid token payload",

        )

    try:

        session_id = PyUUID(session_id_str)

    except ValueError:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Invalid session id in token",

        )

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if session.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired")
    return session

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import CurrentUser
from models.skin import Skin
from schemas.schemas import UserOut, UserUpdate

router = APIRouter()


async def _build_user_out(user, db: AsyncSession) -> UserOut:
    active_piece_code = None
    active_board_code = None
    if user.active_piece_skin_id:
        active_piece_code = (await db.execute(
            select(Skin.code).where(Skin.id == user.active_piece_skin_id)
        )).scalar_one_or_none()
    if user.active_board_skin_id:
        active_board_code = (await db.execute(
            select(Skin.code).where(Skin.id == user.active_board_skin_id)
        )).scalar_one_or_none()
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        surname=user.surname,
        created_at=user.created_at,
        active_piece_skin_code=active_piece_code,
        active_board_skin_code=active_board_code,
    )


@router.get("", response_model=UserOut)
async def get_me(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    return await _build_user_out(user, db)


@router.patch("", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if data.name is not None:
        user.name = data.name
    if data.surname is not None:
        user.surname = data.surname
    await db.commit()
    await db.refresh(user)
    return await _build_user_out(user, db)

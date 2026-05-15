from typing import Annotated, List
from uuid import UUID as PyUUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.dependencies import CurrentUser
from models.skin import Skin, SkinKind, UserSkin
from schemas.schemas import SkinOut, UserSkinOut

router = APIRouter()


def _to_out(skin: Skin, owned_ids: set, active_piece_id, active_board_id) -> SkinOut:
    return SkinOut(
        id=skin.id,
        code=skin.code,
        kind=skin.kind,
        name=skin.name,
        description=skin.description,
        price_kzt=float(skin.price_kzt),
        preview_url=skin.preview_url,
        is_active=skin.is_active,
        owned=skin.id in owned_ids,
        equipped=(skin.id == active_piece_id) or (skin.id == active_board_id),
    )


@router.get("", response_model=List[SkinOut])
async def list_skins(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Catalog with per-user `owned` and `equipped` flags."""
    skins = (
        await db.execute(
            select(Skin).where(Skin.is_active.is_(True)).order_by(Skin.kind, Skin.price_kzt)
        )
    ).scalars().all()

    owned_ids = set((
        await db.execute(
            select(UserSkin.skin_id).where(UserSkin.user_id == user.id)
        )
    ).scalars().all())

    return [
        _to_out(s, owned_ids, user.active_piece_skin_id, user.active_board_skin_id)
        for s in skins
    ]


@router.get("/me", response_model=List[UserSkinOut])
async def list_my_skins(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(UserSkin)
        .where(UserSkin.user_id == user.id)
        .options(selectinload(UserSkin.skin))
        .order_by(UserSkin.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{skin_id}/equip", response_model=SkinOut)
async def equip_skin(
    skin_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    skin = (await db.execute(select(Skin).where(Skin.id == skin_id))).scalars().first()
    if not skin:
        raise HTTPException(404, "Skin not found")

    owned = (await db.execute(
        select(UserSkin).where(UserSkin.user_id == user.id, UserSkin.skin_id == skin.id)
    )).scalars().first()
    if not owned:
        raise HTTPException(403, "You don't own this skin")

    if skin.kind == SkinKind.piece_set:
        user.active_piece_skin_id = skin.id
    elif skin.kind == SkinKind.board:
        user.active_board_skin_id = skin.id
    else:
        raise HTTPException(400, f"Skin kind '{skin.kind}' is not equippable yet")

    await db.commit()

    return _to_out(
        skin,
        owned_ids={skin.id},
        active_piece_id=user.active_piece_skin_id,
        active_board_id=user.active_board_skin_id,
    )


@router.post("/unequip/{kind}", response_model=dict)
async def unequip_kind(
    kind: SkinKind,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return to the default look for the given kind."""
    if kind == SkinKind.piece_set:
        user.active_piece_skin_id = None
    elif kind == SkinKind.board:
        user.active_board_skin_id = None
    else:
        raise HTTPException(400, f"Kind '{kind}' is not equippable")
    await db.commit()
    return {"ok": True, "kind": kind.value}

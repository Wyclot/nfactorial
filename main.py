from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

import models  # noqa: F401 — register all SQLAlchemy models
from api.auth import router as auth_router
from api.game import router as game_router
from api.payments import router as payments_router
from api.skins import router as skins_router
from api.user import router as user_router
from api.ws import router as ws_router
from core.database import AsyncSessionLocal, engine
from models.base import Base
from models.skin import Skin, SkinKind
from models.user import AI_BOT_ID, AI_BOT_NAME, AuthProvider, User


SAMPLE_SKINS = [
    {
        "code": "piece_pearl",
        "kind": SkinKind.piece_set,
        "name": "Pearl Pieces",
        "description": "Iridescent pearl shashki with a soft silver glow.",
        "price_kzt": Decimal("500"),
    },
    {
        "code": "piece_obsidian",
        "kind": SkinKind.piece_set,
        "name": "Obsidian Pieces",
        "description": "Deep glossy black with violet undertones.",
        "price_kzt": Decimal("500"),
    },
    {
        "code": "piece_gold",
        "kind": SkinKind.piece_set,
        "name": "Gold Pieces",
        "description": "Champagne-gold pieces — for the high roller.",
        "price_kzt": Decimal("1000"),
    },
    {
        "code": "board_marble",
        "kind": SkinKind.board,
        "name": "Marble Board",
        "description": "Polished marble light and dark squares.",
        "price_kzt": Decimal("700"),
    },
    {
        "code": "board_ocean",
        "kind": SkinKind.board,
        "name": "Ocean Board",
        "description": "Deep-blue ocean-themed board.",
        "price_kzt": Decimal("600"),
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Seed the AI bot user.
        existing = (await db.execute(select(User).where(User.id == AI_BOT_ID))).scalars().first()
        if not existing:
            db.add(User(
                id=AI_BOT_ID,
                name=AI_BOT_NAME,
                provider=AuthProvider.system,
                provider_user_id="bot",
            ))

        # Seed sample skins (idempotent by `code`).
        existing_codes = set((
            await db.execute(select(Skin.code))
        ).scalars().all())
        for s in SAMPLE_SKINS:
            if s["code"] not in existing_codes:
                db.add(Skin(**s))

        await db.commit()

    yield


app = FastAPI(title="Checkers", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="/me", tags=["me"])
app.include_router(game_router, prefix="/games", tags=["games"])
app.include_router(ws_router, prefix="/ws", tags=["ws"])
app.include_router(skins_router, prefix="/skins", tags=["skins"])
app.include_router(payments_router, prefix="/payments", tags=["payments"])


@app.get("/")
async def root():
    return {"status": "ok"}

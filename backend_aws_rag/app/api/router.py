"""
Central API router — aggregates all endpoint routers into a single include.

Usage in main.py:
    from app.api.router import api_router
    app.include_router(api_router)
"""

from fastapi import APIRouter

from app.api.endpoints import documents, index, search, chat, janaushadhi

api_router = APIRouter()

# ── Include all endpoint routers ─────────────────────────────────────
api_router.include_router(index.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)
api_router.include_router(janaushadhi.router)

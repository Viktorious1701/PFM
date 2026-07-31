"""v1 router aggregate.

Each story appends its router here. Mounted under `settings.api_v1_prefix` by
`main.create_app` (constitution API-01).
"""

from fastapi import APIRouter

from app.api.v1 import users

api_router = APIRouter()
api_router.include_router(users.router)

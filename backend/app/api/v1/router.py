"""v1 router aggregate.

Each story appends its router here. Mounted under `settings.api_v1_prefix` by
`main.create_app` (constitution API-01).
"""

from fastapi import APIRouter

from app.api.v1 import auth, budgets, categories, dev, transactions, users, wallets

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(wallets.router)
api_router.include_router(categories.router)
api_router.include_router(budgets.router)
api_router.include_router(transactions.router)
api_router.include_router(dev.router)

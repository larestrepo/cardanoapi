from fastapi import APIRouter

from .endpoints import admin_api, blockchain_api, keys_api, transactions_api, scripts_api, security, oracle_api


api_router = APIRouter()
api_router.include_router(security.router, prefix="/security", tags=["Security"])
api_router.include_router(admin_api.router, prefix="/admin", tags=["Admin"])
api_router.include_router(blockchain_api.router, prefix="/blockchain", tags=["Blockchain"])
api_router.include_router(keys_api.router, prefix="/keys", tags=["Keys"])
api_router.include_router(transactions_api.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(scripts_api.router, prefix="/scripts", tags=["Scripts"])
api_router.include_router(oracle_api.router, prefix="/oracle", tags=["Oracle"])
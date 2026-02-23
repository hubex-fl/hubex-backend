# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as v1_router
from app.api.v1.telemetry import ws_router as telemetry_ws_router
from app.core.modules import sync_module_registry
from app.db.session import AsyncSessionLocal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")
app.include_router(telemetry_ws_router, prefix="/api/v1")

@app.on_event("startup")
async def _startup_sync_modules() -> None:
    async with AsyncSessionLocal() as db:
        await sync_module_registry(db)

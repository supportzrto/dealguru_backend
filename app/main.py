from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine
from app.routers.products import router as products_router
from fastapi.middleware.cors import CORSMiddleware
from app.routers.auth import router as auth_router
from app.routers import addresses
from app.routers.orders import router as orders_router
from app.config import settings
# redirect_slashes=False: a 307 slash-redirect on a cross-site request drops the auth cookie
app = FastAPI(title="DealGuru API", version="0.1.0", redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
         "https://dealgurufrontend.vercel.app",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(auth_router)
app.include_router(addresses.router)
app.include_router(orders_router)

@app.get("/")
def root():
    return {"message": "DealGuru API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from exc

    
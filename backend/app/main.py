from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import Base, engine
from app.routers import auth, bots, trades, strategies, market, alerts, exchanges

# Note: Table creation is managed via Alembic migrations,
# but we can also run Base.metadata.create_all for local SQLite fallback if needed
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Trading Bot API",
    description="AI-powered trading bot ecosystem",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(exchanges.router)
app.include_router(bots.router)
app.include_router(trades.router)
app.include_router(strategies.router)
app.include_router(market.router)
app.include_router(alerts.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

from fastapi import APIRouter, HTTPException, Query
from app.services.market_data import MarketDataService
from typing import Dict, Any, List

router = APIRouter(prefix="/market", tags=["market"])

@router.get("/ticker")
def get_ticker(
    exchange: str = Query(..., description="Exchange name, e.g., binance, bybit, kucoin"),
    pair: str = Query(..., description="Trading pair, e.g., BTC/USDT"),
    sandbox: bool = Query(True, description="Use sandbox/testnet mode")
):
    try:
        service = MarketDataService(exchange_name=exchange, sandbox=sandbox)
        return service.fetch_ticker(pair)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/candles")
def get_candles(
    exchange: str = Query(..., description="Exchange name"),
    pair: str = Query(..., description="Trading pair"),
    timeframe: str = Query("1h", description="Candle timeframe, e.g., 1m, 5m, 1h, 1d"),
    limit: int = Query(200, ge=1, le=1000),
    sandbox: bool = Query(True)
):
    try:
        service = MarketDataService(exchange_name=exchange, sandbox=sandbox)
        df = service.fetch_ohlcv(pair, timeframe, limit)
        # Convert DataFrame to records dict
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/orderbook")
def get_orderbook(
    exchange: str = Query(..., description="Exchange name"),
    pair: str = Query(..., description="Trading pair"),
    limit: int = Query(20, ge=1, le=100),
    sandbox: bool = Query(True)
):
    try:
        service = MarketDataService(exchange_name=exchange, sandbox=sandbox)
        return service.fetch_orderbook(pair, limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

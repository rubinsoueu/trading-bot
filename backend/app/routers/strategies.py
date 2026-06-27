from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from app.services.strategy_engine import StrategyEngine
from app.services.market_data import MarketDataService
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/strategies", tags=["strategies"])

class BacktestRequest(BaseModel):
    strategy_name: str
    exchange: str
    pair: str
    timeframe: str = "1h"
    limit: int = 500
    initial_capital: float = 10000.0
    commission_pct: float = 0.001
    parameters: Optional[Dict[str, Any]] = None

@router.get("/")
def list_strategies():
    """
    Returns list of built-in technical strategies.
    """
    return [
        {
            "name": "sma_crossover",
            "display_name": "SMA Crossover",
            "description": "Double SMA moving average crossover strategy. Buy when fast SMA crosses above slow SMA, sell when crosses below.",
            "parameters": {
                "fast_window": {"type": "int", "default": 20},
                "slow_window": {"type": "int", "default": 50}
            }
        },
        {
            "name": "rsi_reversion",
            "display_name": "RSI Mean Reversion",
            "description": "Mean reversion based on RSI overbought (>70) and oversold (<30) thresholds.",
            "parameters": {
                "rsi_period": {"type": "int", "default": 14},
                "oversold": {"type": "float", "default": 30.0},
                "overbought": {"type": "float", "default": 70.0}
            }
        }
    ]

@router.post("/backtest")
def run_backtest(req: BacktestRequest):
    try:
        # 1. Fetch historical OHLCV data
        market_service = MarketDataService(exchange_name=req.exchange, sandbox=True)
        ohlcv_df = market_service.fetch_ohlcv(req.pair, req.timeframe, req.limit)
        
        # 2. Run backtest
        params = req.parameters or {}
        result = StrategyEngine.backtest(
            strategy_name=req.strategy_name,
            ohlcv_df=ohlcv_df,
            initial_capital=req.initial_capital,
            commission_pct=req.commission_pct,
            **params
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

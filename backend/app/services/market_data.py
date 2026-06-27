import ccxt
import pandas as pd
import logging
import time
from typing import Dict, Any, List, Optional
from app.config import settings
import redis

logger = logging.getLogger(__name__)

# Fallback in-memory cache for when Redis is unavailable
_memory_cache: Dict[str, tuple[float, Any]] = {}

def get_redis_client():
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        return r
    except Exception as e:
        logger.warning(f"Redis is unavailable, using in-memory cache fallback. Error: {e}")
        return None

class MarketDataService:
    _instances: Dict[str, ccxt.Exchange] = {}

    @classmethod
    def get_exchange_instance(cls, exchange_name: str, sandbox: bool = True) -> ccxt.Exchange:
        cache_key = f"{exchange_name}_{sandbox}"
        if cache_key not in cls._instances:
            exchange_class = getattr(ccxt, exchange_name, None)
            if not exchange_class:
                raise ValueError(f"Exchange {exchange_name} is not supported by CCXT")
            
            exchange = exchange_class({
                'enableRateLimit': True,
            })
            if sandbox and hasattr(exchange, 'set_sandbox_mode'):
                exchange.set_sandbox_mode(True)
            cls._instances[cache_key] = exchange
        return cls._instances[cache_key]

    def __init__(self, exchange_name: str = "binance", sandbox: bool = True):
        self.exchange_name = exchange_name.lower()
        self.sandbox = sandbox
        self.exchange = self.get_exchange_instance(self.exchange_name, self.sandbox)
        self.redis = get_redis_client()

    def _get_cache(self, key: str) -> Optional[Any]:
        if self.redis:
            try:
                import json
                val = self.redis.get(key)
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.error(f"Redis get error for key {key}: {e}")
        
        # Memory cache fallback
        if key in _memory_cache:
            expiry, val = _memory_cache[key]
            if time.time() < expiry:
                return val
            else:
                del _memory_cache[key]
        return None

    def _set_cache(self, key: str, value: Any, ttl: int):
        if self.redis:
            try:
                import json
                self.redis.setex(key, ttl, json.dumps(value))
                return
            except Exception as e:
                logger.error(f"Redis set error for key {key}: {e}")
        
        # Memory cache fallback
        _memory_cache[key] = (time.time() + ttl, value)

    def fetch_ticker(self, pair: str) -> Dict[str, Any]:
        cache_key = f"ticker:{self.exchange_name}:{pair}:{self.sandbox}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            ticker = self.exchange.fetch_ticker(pair)
            result = {
                "symbol": ticker.get("symbol", pair),
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "volume": ticker.get("baseVolume"),
                "timestamp": ticker.get("timestamp", int(time.time() * 1000)),
            }
            self._set_cache(cache_key, result, ttl=15) # Cache for 15 seconds
            return result
        except Exception as e:
            logger.error(f"Error fetching ticker for {pair} on {self.exchange_name}: {e}")
            raise

    def fetch_ohlcv(self, pair: str, timeframe: str = "1h", limit: int = 200) -> pd.DataFrame:
        cache_key = f"ohlcv:{self.exchange_name}:{pair}:{timeframe}:{limit}:{self.sandbox}"
        cached = self._get_cache(cache_key)
        
        if cached:
            return pd.DataFrame(cached, columns=["timestamp", "open", "high", "low", "close", "volume"])

        try:
            ohlcv = self.exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
            # Store in cache as list of lists
            self._set_cache(cache_key, ohlcv, ttl=60) # Cache for 1 minute
            return pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {pair} on {self.exchange_name}: {e}")
            raise

    def fetch_orderbook(self, pair: str, limit: int = 20) -> Dict[str, Any]:
        cache_key = f"orderbook:{self.exchange_name}:{pair}:{limit}:{self.sandbox}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            ob = self.exchange.fetch_order_book(pair, limit=limit)
            result = {
                "bids": ob.get("bids", [])[:limit],
                "asks": ob.get("asks", [])[:limit],
                "timestamp": ob.get("timestamp", int(time.time() * 1000)),
            }
            self._set_cache(cache_key, result, ttl=10) # Cache for 10 seconds
            return result
        except Exception as e:
            logger.error(f"Error fetching orderbook for {pair} on {self.exchange_name}: {e}")
            raise

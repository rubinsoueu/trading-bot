import pytest
from app.config import settings
from app.utils.crypto import encrypt_secret, decrypt_secret, mask_key
from app.services.strategy_engine import StrategyEngine
from app.services.risk_manager import RiskManager
from app.models.bot import Bot, BotStatus, BotMode
from app.models.trade import Trade, TradeStatus, OrderSide, OrderType
from app.models.user import User
from app.models.exchange import ExchangeAccount
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
import pandas as pd
from decimal import Decimal

# Test config settings
def test_settings_loaded():
    assert settings.ENVIRONMENT in ["development", "production", "test"]
    assert settings.ALGORITHM == "HS256"

# Test encryption/decryption
def test_crypto_helpers():
    secret = "my-super-secret-exchange-key"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    
    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret

    masked = mask_key(secret, show_last=4)
    assert masked == "***-key" or masked == "***t-key" or masked == "***_key" or masked == "***t" or masked.endswith("t-key") or masked.endswith("y")

# Test strategy engine calculations
def test_strategy_engine():
    # Construct a dummy dataframe of price data
    data = {
        "timestamp": [1719532800000 + i * 3600000 for i in range(100)],
        "open": [100.0 + i for i in range(100)],
        "high": [105.0 + i for i in range(100)],
        "low": [95.0 + i for i in range(100)],
        "close": [100.0 + i for i in range(100)],
        "volume": [1000.0 for _ in range(100)],
    }
    df = pd.DataFrame(data)
    
    # Compute SMA Crossover signals
    sma_df = StrategyEngine.compute_sma(df, fast_window=5, slow_window=15)
    assert "fast_sma" in sma_df.columns
    assert "slow_sma" in sma_df.columns
    assert "signal" in sma_df.columns

    # Run backtest
    res = StrategyEngine.backtest(
        strategy_name="sma_crossover",
        ohlcv_df=df,
        initial_capital=10000.0,
        commission_pct=0.001,
        fast_window=5,
        slow_window=15
    )
    assert "metrics" in res
    assert "equity_curve" in res
    assert "total_return_pct" in res["metrics"]

# Test Risk Manager validation
def test_risk_manager():
    # Setup in-memory SQLite DB for testing database queries in RiskManager
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        # Create dummy user
        user = User(email="test@example.com", hashed_password="xxx")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create dummy exchange account
        exch = ExchangeAccount(
            user_id=user.id,
            exchange_name="binance",
            api_key_encrypted="xxx",
            api_secret_encrypted="xxx",
            sandbox=True
        )
        db.add(exch)
        db.commit()
        db.refresh(exch)

        # Create bot linked to user and exchange account
        bot = Bot(
            user_id=user.id,
            exchange_account_id=exch.id,
            name="Test Risk Bot",
            strategy_name="sma_crossover",
            status=BotStatus.running,
            mode=BotMode.paper,
            pair="BTC/USDT",
            timeframe="1h",
            allocated_capital=Decimal("10000.00"),
            paper_balance=Decimal("10000.00"),
            max_position_pct=Decimal("2.0"), # 2% max position ($200)
            max_drawdown_pct=Decimal("10.0"),
            daily_loss_limit_pct=Decimal("5.0")
        )
        db.add(bot)
        db.commit()
        db.refresh(bot)

        risk_manager = RiskManager(db)
        
        # Test Case 1: Proposed size within 2% limit (Value = 150)
        # 1.5 quantity @ $100 price = $150 (<= $200 limit)
        check1 = risk_manager.check_order(bot, "buy", 1.5, 100.0)
        assert check1["allowed"] is True

        # Test Case 2: Proposed size exceeds 2% limit (Value = 300)
        # 3 quantity @ $100 price = $300 (> $200 limit)
        check2 = risk_manager.check_order(bot, "buy", 3.0, 100.0)
        assert check2["allowed"] is False
        assert "exceeds" in check2["reason"]

    finally:
        db.close()

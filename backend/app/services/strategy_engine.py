import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class StrategyEngine:
    @staticmethod
    def compute_sma(df: pd.DataFrame, fast_window: int = 20, slow_window: int = 50) -> pd.DataFrame:
        df = df.copy()
        df['fast_sma'] = df['close'].rolling(window=fast_window).mean()
        df['slow_sma'] = df['close'].rolling(window=slow_window).mean()
        
        df['signal'] = 0
        # Buy signal (1): fast SMA crosses above slow SMA
        # Sell signal (-1): fast SMA crosses below slow SMA
        df.loc[df['fast_sma'] > df['slow_sma'], 'signal'] = 1
        df.loc[df['fast_sma'] < df['slow_sma'], 'signal'] = -1
        return df

    @staticmethod
    def compute_rsi(df: pd.DataFrame, period: int = 14, oversold: float = 30, overbought: float = 70) -> pd.DataFrame:
        df = df.copy()
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df['signal'] = 0
        df.loc[df['rsi'] < oversold, 'signal'] = 1   # Buy signal on oversold
        df.loc[df['rsi'] > overbought, 'signal'] = -1 # Sell signal on overbought
        return df

    @classmethod
    def backtest(
        cls,
        strategy_name: str,
        ohlcv_df: pd.DataFrame,
        initial_capital: float = 10000.0,
        commission_pct: float = 0.001,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Runs a vectorized backtest on historical OHLCV data.
        Returns performance metrics and equity curve.
        """
        if ohlcv_df.empty or len(ohlcv_df) < 50:
            return {"error": "Insufficient data to run backtest"}

        # Generate signals
        if strategy_name.lower() == "sma_crossover":
            fast = int(kwargs.get("fast_window", 20))
            slow = int(kwargs.get("slow_window", 50))
            df = cls.compute_sma(ohlcv_df, fast, slow)
        elif strategy_name.lower() == "rsi_reversion":
            period = int(kwargs.get("rsi_period", 14))
            oversold = float(kwargs.get("oversold", 30))
            overbought = float(kwargs.get("overbought", 70))
            df = cls.compute_rsi(ohlcv_df, period, oversold, overbought)
        else:
            return {"error": f"Unknown strategy {strategy_name}"}

        df['returns'] = df['close'].pct_change()
        
        # Position tracking (forward fill signals to hold positions)
        df['position'] = df['signal'].shift(1).fillna(0)
        df['position'] = df['position'].replace(to_replace=0, method='ffill')

        # Compute strategy returns
        df['strategy_returns'] = df['position'] * df['returns']
        
        # Apply commission on transaction changes
        df['trade_type'] = df['position'].diff().fillna(0)
        df['transaction_cost'] = np.where(df['trade_type'] != 0, commission_pct, 0.0)
        df['strategy_returns'] = df['strategy_returns'] - df['transaction_cost']

        # Cumulative equity curve
        df['cum_returns'] = (1 + df['strategy_returns']).cumprod()
        df['equity'] = initial_capital * df['cum_returns'].fillna(1.0)
        
        # Metrics
        total_return = (df['equity'].iloc[-1] - initial_capital) / initial_capital * 100
        
        # Win rate
        closed_trades = df[df['trade_type'] != 0]
        trade_returns = df.loc[df['trade_type'] != 0, 'strategy_returns']
        win_rate = (trade_returns > 0).mean() * 100 if len(trade_returns) > 0 else 0.0
        
        # Sharpe ratio
        daily_std = df['strategy_returns'].std()
        sharpe = (df['strategy_returns'].mean() / daily_std * np.sqrt(365)) if daily_std > 0 else 0.0
        
        # Max drawdown
        df['peak'] = df['equity'].cummax()
        df['drawdown'] = (df['equity'] - df['peak']) / df['peak']
        max_drawdown = df['drawdown'].min() * 100

        # Build equity curve chart data
        equity_curve = []
        for index, row in df.iterrows():
            equity_curve.append({
                "timestamp": int(row['timestamp']),
                "equity": float(row['equity']),
                "price": float(row['close']),
            })

        return {
            "strategy": strategy_name,
            "metrics": {
                "total_return_pct": round(total_return, 2),
                "sharpe_ratio": round(sharpe, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "win_rate_pct": round(win_rate, 2),
                "total_trades": int((df['trade_type'] != 0).sum()),
                "final_capital": round(df['equity'].iloc[-1], 2),
            },
            "equity_curve": equity_curve
        }

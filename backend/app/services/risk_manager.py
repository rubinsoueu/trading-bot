from app.models.bot import Bot
from app.models.trade import Trade, TradeStatus
from sqlalchemy.orm import Session
from datetime import datetime, date
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, db: Session):
        self.db = db

    def check_order(self, bot: Bot, proposed_side: str, proposed_amount: float, current_price: float) -> dict:
        """
        Validates if placing an order satisfies the risk management rules:
        - Max position: 2% of allocated capital per trade (proposed_amount * price <= 2% capital)
        - Daily loss limit: 5% of allocated capital max loss today
        - Max drawdown limit: 10% from peak equity
        Returns {"allowed": bool, "reason": str}
        """
        allocated_capital = float(bot.allocated_capital)
        proposed_value = proposed_amount * current_price

        # 1. Position Sizing Check (Proposed trade value cannot exceed max_position_pct of capital)
        max_position_pct = float(bot.max_position_pct or 2.0)
        max_position_val = allocated_capital * (max_position_pct / 100.0)
        if proposed_value > max_position_val:
            return {
                "allowed": False,
                "reason": f"Position size {round(proposed_value, 2)} exceeds {max_position_pct}% of capital ({round(max_position_val, 2)})"
            }

        # 2. Daily Loss Limit Check
        # Query bot's trades completed today
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_trades = self.db.query(Trade).filter(
            Trade.bot_id == bot.id,
            Trade.status == TradeStatus.closed,
            Trade.closed_at >= today_start
        ).all()
        
        daily_pnl = sum([float(t.pnl or 0) for t in today_trades])
        daily_loss_limit_pct = float(bot.daily_loss_limit_pct or 5.0)
        max_daily_loss_val = allocated_capital * (daily_loss_limit_pct / 100.0)

        # If today's realized loss exceeds limit
        if daily_pnl < 0 and abs(daily_pnl) >= max_daily_loss_val:
            return {
                "allowed": False,
                "reason": f"Daily loss limit of {daily_loss_limit_pct}% ({round(max_daily_loss_val, 2)}) reached. Today P&L: {round(daily_pnl, 2)}"
            }

        # 3. Max Drawdown Check
        # Drawdown is calculated based on current balance vs peak balance (allocated capital is initial)
        current_balance = float(bot.paper_balance) if bot.paper_balance is not None else allocated_capital
        # Peak equity is the highest paper_balance reached or initial capital
        # To get the peak equity, we can check bot history or compute from trades.
        # Let's simple approximate or load from a history table.
        # For simplicity, we can load all trades and calculate peak balance from inception.
        all_trades = self.db.query(Trade).filter(
            Trade.bot_id == bot.id,
            Trade.status == TradeStatus.closed
        ).order_by(Trade.closed_at.asc()).all()

        peak_equity = allocated_capital
        running_equity = allocated_capital
        
        for trade in all_trades:
            running_equity += float(trade.pnl or 0)
            if running_equity > peak_equity:
                peak_equity = running_equity

        # Current equity is capital + all closed trades P&L
        current_equity = running_equity
        drawdown_pct = 0.0
        if peak_equity > 0:
            drawdown_pct = ((peak_equity - current_equity) / peak_equity) * 100.0

        max_drawdown_pct = float(bot.max_drawdown_pct or 10.0)
        if drawdown_pct >= max_drawdown_pct:
            return {
                "allowed": False,
                "reason": f"Max drawdown limit of {max_drawdown_pct}% exceeded. Current drawdown: {round(drawdown_pct, 2)}% (Peak: {round(peak_equity, 2)}, Current: {round(current_equity, 2)})"
            }

        return {"allowed": True, "reason": "Passed all risk checks"}

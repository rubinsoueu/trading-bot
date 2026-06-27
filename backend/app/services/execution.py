import logging
from sqlalchemy.orm import Session
from app.models.bot import Bot, BotMode
from app.models.trade import Trade, TradeStatus, OrderSide, OrderType
from app.models.exchange import ExchangeAccount
from app.utils.crypto import decrypt_secret
from app.services.market_data import MarketDataService
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
import ccxt

logger = logging.getLogger(__name__)

class ExecutionService:
    def __init__(self, db: Session):
        self.db = db

    def _get_ccxt_exchange(self, bot: Bot) -> ccxt.Exchange:
        """
        Loads exchange keys, decrypts them, and returns an authenticated CCXT instance.
        """
        # Load exchange account details
        exchange_acc = self.db.query(ExchangeAccount).filter(
            ExchangeAccount.id == bot.exchange_account_id
        ).first()

        if not exchange_acc:
            raise ValueError(f"Exchange account details not found for bot {bot.name}")

        exchange_name = exchange_acc.exchange_name.lower()
        api_key = decrypt_secret(exchange_acc.api_key_encrypted)
        api_secret = decrypt_secret(exchange_acc.api_secret_encrypted)

        exchange_class = getattr(ccxt, exchange_name, None)
        if not exchange_class:
            raise ValueError(f"Exchange {exchange_name} is not supported by CCXT")

        exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        # Set sandbox mode
        if exchange_acc.sandbox and hasattr(exchange, 'set_sandbox_mode'):
            exchange.set_sandbox_mode(True)
            
        return exchange

    def execute_order(
        self,
        bot: Bot,
        side: str,
        order_type: str,
        pair: str,
        quantity: float,
        price: float
    ) -> Dict[str, Any]:
        """
        Executes order in either Paper or Live trading mode.
        """
        if bot.mode == BotMode.paper:
            return self._execute_paper(bot, side, order_type, pair, quantity, price)
        else:
            return self._execute_live(bot, side, order_type, pair, quantity, price)

    def _execute_paper(
        self,
        bot: Bot,
        side: str,
        order_type: str,
        pair: str,
        quantity: float,
        price: float
    ) -> Dict[str, Any]:
        """
        Simulates order execution locally in SQLite database.
        """
        logger.info(f"[PAPER] Executing {side} order for {bot.name} - {quantity} {pair} @ {price}")
        
        # Ensure paper_balance is initialized
        if bot.paper_balance is None:
            bot.paper_balance = bot.allocated_capital
            
        paper_bal = float(bot.paper_balance)
        cost = quantity * price

        if side == "buy" and paper_bal < cost:
            return {"success": False, "error": "Insufficient paper balance"}

        # Create simulated trade
        trade = Trade(
            bot_id=bot.id,
            exchange="paper_sim",
            order_id=f"paper_{datetime.utcnow().timestamp()}",
            side=OrderSide.buy if side == "buy" else OrderSide.sell,
            pair=pair,
            type=OrderType.market if order_type == "market" else OrderType.limit,
            price=Decimal(str(price)),
            quantity=Decimal(str(quantity)),
            fee=Decimal("0.0"),
            fee_currency=pair.split("/")[1] if "/" in pair else "USDT",
            status=TradeStatus.open if side == "buy" else TradeStatus.closed,
            opened_at=datetime.utcnow()
        )

        if side == "buy":
            # Subtract balance
            bot.paper_balance = Decimal(str(paper_bal - cost))
            self.db.add(trade)
        else:
            # Side is Sell - close previous open buy trades
            open_trades = self.db.query(Trade).filter(
                Trade.bot_id == bot.id,
                Trade.side == OrderSide.buy,
                Trade.status == TradeStatus.open
            ).all()

            total_pnl = 0.0
            for open_t in open_trades:
                buy_cost = float(open_t.price) * float(open_t.quantity)
                sell_value = price * float(open_t.quantity)
                pnl = sell_value - buy_cost
                total_pnl += pnl
                
                open_t.status = TradeStatus.closed
                open_t.closed_at = datetime.utcnow()
                open_t.pnl = Decimal(str(pnl))

            # Add to balance: cost of sales + profits
            bot.paper_balance = Decimal(str(paper_bal + cost))
            trade.pnl = Decimal(str(total_pnl))
            trade.closed_at = datetime.utcnow()
            self.db.add(trade)

        self.db.commit()
        return {"success": True, "trade_id": str(trade.id), "pnl": trade.pnl}

    def _execute_live(
        self,
        bot: Bot,
        side: str,
        order_type: str,
        pair: str,
        quantity: float,
        price: float
    ) -> Dict[str, Any]:
        """
        Executes order live on the real exchange using CCXT.
        """
        logger.info(f"[LIVE] Executing {side} order on exchange for {bot.name}")
        try:
            exchange = self._get_ccxt_exchange(bot)
            
            # Place order on exchange
            if side == "buy":
                if order_type == "market":
                    order = exchange.create_market_buy_order(pair, quantity)
                else:
                    order = exchange.create_limit_buy_order(pair, quantity, price)
            else:
                if order_type == "market":
                    order = exchange.create_market_sell_order(pair, quantity)
                else:
                    order = exchange.create_limit_sell_order(pair, quantity, price)

            # Record in DB
            trade = Trade(
                bot_id=bot.id,
                exchange=bot.exchange_account_id, # exchange identifier
                order_id=order.get("id"),
                side=OrderSide.buy if side == "buy" else OrderSide.sell,
                pair=pair,
                type=OrderType.market if order_type == "market" else OrderType.limit,
                price=Decimal(str(order.get("price") or price)),
                quantity=Decimal(str(order.get("amount") or quantity)),
                fee=Decimal(str(order.get("fee", {}).get("cost", 0.0) or 0.0)),
                fee_currency=order.get("fee", {}).get("currency", "USDT"),
                status=TradeStatus.open if side == "buy" else TradeStatus.closed,
                opened_at=datetime.utcnow()
            )

            if side == "sell":
                # Close previous open buy trades
                open_trades = self.db.query(Trade).filter(
                    Trade.bot_id == bot.id,
                    Trade.side == OrderSide.buy,
                    Trade.status == TradeStatus.open
                ).all()

                total_pnl = 0.0
                for open_t in open_trades:
                    buy_cost = float(open_t.price) * float(open_t.quantity)
                    sell_value = price * float(open_t.quantity)
                    pnl = sell_value - buy_cost
                    total_pnl += pnl
                    
                    open_t.status = TradeStatus.closed
                    open_t.closed_at = datetime.utcnow()
                    open_t.pnl = Decimal(str(pnl))
                
                trade.pnl = Decimal(str(total_pnl))
                trade.closed_at = datetime.utcnow()

            self.db.add(trade)
            self.db.commit()
            return {"success": True, "order": order, "trade_id": str(trade.id)}

        except Exception as e:
            logger.error(f"Live trade execution failed: {e}")
            return {"success": False, "error": str(e)}

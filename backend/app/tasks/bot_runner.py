import logging
from celery import shared_task
from app.database import SessionLocal
from app.models.bot import Bot, BotStatus
from app.services.market_data import MarketDataService
from app.services.strategy_engine import StrategyEngine
from app.services.ai_signal import AISignalService
from app.services.risk_manager import RiskManager
from app.services.execution import ExecutionService
from app.services.alerting import AlertingService
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

@shared_task(name="app.tasks.bot_runner.run_bot_task")
def run_bot_task(bot_id: str):
    """
    Executes a single trading tick for a given bot.
    """
    db = SessionLocal()
    try:
        bot = db.query(Bot).filter(Bot.id == uuid.UUID(bot_id)).first()
        if not bot:
            logger.error(f"Bot {bot_id} not found in database")
            return
            
        if bot.status != BotStatus.running:
            logger.info(f"Bot {bot.name} is not running (status: {bot.status})")
            return

        logger.info(f"Running trading tick for bot: {bot.name} [{bot.pair} - {bot.timeframe}]")

        # 1. Fetch market data
        market_service = MarketDataService(exchange_name="binance", sandbox=True) # default to binance sandbox
        df = market_service.fetch_ohlcv(bot.pair, bot.timeframe, limit=100)
        
        if df.empty or len(df) < 20:
            logger.warning(f"Insufficient candles for {bot.pair}")
            return

        # 2. Calculate Indicators
        df = StrategyEngine.compute_rsi(df, period=14)
        df = StrategyEngine.compute_sma(df, fast_window=20, slow_window=50)
        
        last_row = df.iloc[-1]
        close_prices = df['close'].tolist()
        rsi_val = float(last_row.get('rsi', 50))
        
        # Calculate mock/simple MACD for prompts
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal_line']
        
        last_row = df.iloc[-1]
        macd_info = {
            "macd": float(last_row.get('macd', 0)),
            "signal": float(last_row.get('signal_line', 0)),
            "histogram": float(last_row.get('histogram', 0))
        }

        # 3. Strategy Signal Generation
        signal_action = "hold"
        confidence = 0.5
        reason = "No signal"

        strategy = bot.strategy_name.lower()
        if strategy == "sma_crossover":
            sig = int(last_row.get('signal', 0))
            if sig == 1:
                signal_action = "buy"
                reason = "Fast SMA crossed above slow SMA (Golden Cross)"
            elif sig == -1:
                signal_action = "sell"
                reason = "Fast SMA crossed below slow SMA (Death Cross)"
        elif strategy == "rsi_reversion":
            sig = int(last_row.get('signal', 0))
            if sig == 1:
                signal_action = "buy"
                reason = f"RSI oversold ({round(rsi_val, 2)} < 30)"
            elif sig == -1:
                signal_action = "sell"
                reason = f"RSI overbought ({round(rsi_val, 2)} > 70)"
        elif strategy == "ai_sentiment":
            ai_service = AISignalService()
            ai_result = ai_service.generate_signal(
                exchange="binance",
                pair=bot.pair,
                timeframe=bot.timeframe,
                close_prices=close_prices,
                rsi_val=rsi_val,
                macd_info=macd_info
            )
            signal_action = ai_result.get("action", "hold")
            confidence = ai_result.get("confidence", 0.5)
            reason = ai_result.get("reason", "AI Signal")
            
        logger.info(f"Signal generated: {signal_action.upper()} (Confidence: {confidence}) - Reason: {reason}")

        # Update bot heartbeat
        bot.last_heartbeat = datetime.utcnow()
        db.commit()

        if signal_action == "hold":
            return

        # 4. Check Risk Manager
        risk_manager = RiskManager(db)
        current_price = float(close_prices[-1])
        
        # Calculate amount to trade (e.g. 2% of paper balance/capital)
        capital = float(bot.paper_balance if bot.paper_balance is not None else bot.allocated_capital)
        max_pos_pct = float(bot.max_position_pct or 2.0)
        trade_value = capital * (max_pos_pct / 100.0)
        quantity = trade_value / current_price

        risk_check = risk_manager.check_order(bot, signal_action, quantity, current_price)
        if not risk_check["allowed"]:
            logger.warning(f"Order rejected by Risk Manager: {risk_check['reason']}")
            # Send risk violation alert
            alert_service = AlertingService(db)
            alert_service.send_alert(
                event_type="RISK_LIMIT_HIT",
                message=f"Bot {bot.name} order rejected: {risk_check['reason']}"
            )
            return

        # 5. Execute Order
        execution_service = ExecutionService(db)
        exec_res = execution_service.execute_order(
            bot=bot,
            side=signal_action,
            order_type="market",
            pair=bot.pair,
            quantity=quantity,
            price=current_price
        )

        if exec_res.get("success"):
            logger.info(f"Order executed successfully! Trade ID: {exec_res.get('trade_id')}")
            # Send execution alert
            alert_service = AlertingService(db)
            alert_service.send_alert(
                event_type="TRADE_EXECUTED",
                message=f"Bot <b>{bot.name}</b> successfully executed a <b>{signal_action.upper()}</b> order for {round(quantity, 4)} {bot.pair} @ {round(current_price, 2)}\nReason: {reason}"
            )
        else:
            logger.error(f"Execution failed: {exec_res.get('error')}")
            alert_service = AlertingService(db)
            alert_service.send_alert(
                event_type="TRADE_FAILED",
                message=f"Bot {bot.name} failed to execute {signal_action.upper()} order: {exec_res.get('error')}"
            )

    except Exception as e:
        logger.error(f"Error in run_bot_task for bot {bot_id}: {e}", exc_info=True)
    finally:
        db.close()

@shared_task(name="app.tasks.bot_runner.run_all_active_bots")
def run_all_active_bots():
    """
    Celery Beat periodic task that schedules evaluation for all active bots.
    """
    db = SessionLocal()
    try:
        active_bots = db.query(Bot).filter(Bot.status == BotStatus.running).all()
        logger.info(f"Celery Beat: Triggering ticks for {len(active_bots)} active bots")
        for bot in active_bots:
            run_bot_task.delay(str(bot.id))
    except Exception as e:
        logger.error(f"Error triggering active bots: {e}")
    finally:
        db.close()

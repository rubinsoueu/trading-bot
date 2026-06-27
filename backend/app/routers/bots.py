from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.bot import Bot, BotStatus, BotMode
from app.models.exchange import ExchangeAccount
from app.routers.auth import get_current_user_db
from app.models.user import User
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bots", tags=["bots"])

class BotCreate(BaseModel):
    name: str
    exchange_account_id: str
    strategy_name: str
    pair: str
    timeframe: str = "1h"
    allocated_capital: float
    mode: BotMode = BotMode.paper
    max_position_pct: float = 2.0
    max_drawdown_pct: float = 10.0
    daily_loss_limit_pct: float = 5.0

class BotResponse(BaseModel):
    id: uuid.UUID
    name: str
    exchange_account_id: uuid.UUID
    strategy_name: str
    status: BotStatus
    mode: BotMode
    pair: str
    timeframe: str
    allocated_capital: float
    paper_balance: Optional[float]
    max_position_pct: float
    max_drawdown_pct: float
    daily_loss_limit_pct: float
    created_at: datetime
    last_heartbeat: Optional[datetime]

    class Config:
        from_attributes = True

@router.get("/", response_model=List[BotResponse])
def list_bots(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_db)):
    bots = db.query(Bot).filter(Bot.user_id == current_user.id).all()
    return bots

@router.post("/", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
def create_bot(bot_in: BotCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_db)):
    # Verify exchange account exists
    exchange_acc = db.query(ExchangeAccount).filter(
        ExchangeAccount.id == uuid.UUID(bot_in.exchange_account_id),
        ExchangeAccount.user_id == current_user.id
    ).first()
    
    if not exchange_acc:
        raise HTTPException(status_code=400, detail="Exchange account not found")

    bot = Bot(
        user_id=current_user.id,
        exchange_account_id=exchange_acc.id,
        name=bot_in.name,
        strategy_name=bot_in.strategy_name,
        status=BotStatus.idle,
        mode=bot_in.mode,
        pair=bot_in.pair,
        timeframe=bot_in.timeframe,
        allocated_capital=Decimal(str(bot_in.allocated_capital)),
        paper_balance=Decimal(str(bot_in.allocated_capital)), # initialize paper balance
        max_position_pct=Decimal(str(bot_in.max_position_pct)),
        max_drawdown_pct=Decimal(str(bot_in.max_drawdown_pct)),
        daily_loss_limit_pct=Decimal(str(bot_in.daily_loss_limit_pct)),
        created_at=datetime.utcnow()
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot

@router.get("/{bot_id}", response_model=BotResponse)
def get_bot(bot_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_db)):
    bot = db.query(Bot).filter(
        Bot.id == uuid.UUID(bot_id),
        Bot.user_id == current_user.id
    ).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot

@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bot(bot_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_db)):
    bot = db.query(Bot).filter(
        Bot.id == uuid.UUID(bot_id),
        Bot.user_id == current_user.id
    ).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # If running, stop first
    if bot.status == BotStatus.running:
        bot.status = BotStatus.stopped
        
    db.delete(bot)
    db.commit()
    return None

@router.post("/{bot_id}/start", response_model=BotResponse)
def start_bot(bot_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_db)):
    bot = db.query(Bot).filter(
        Bot.id == uuid.UUID(bot_id),
        Bot.user_id == current_user.id
    ).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    bot.status = BotStatus.running
    bot.last_heartbeat = datetime.utcnow()
    db.commit()
    
    # Celery task trigger
    try:
        from app.tasks.bot_runner import run_bot_task
        # Try triggering asynchronously, if redis/celery is missing log it
        run_bot_task.delay(str(bot.id))
    except Exception as e:
        logger.warning(f"Could not trigger Celery task run_bot_task: {e}. Bot state updated in DB. Will rely on periodic/manual tick loops.")

    db.refresh(bot)
    return bot

@router.post("/{bot_id}/stop", response_model=BotResponse)
def stop_bot(bot_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_db)):
    bot = db.query(Bot).filter(
        Bot.id == uuid.UUID(bot_id),
        Bot.user_id == current_user.id
    ).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    bot.status = BotStatus.stopped
    db.commit()
    db.refresh(bot)
    return bot

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.trade import Trade, TradeStatus, OrderSide, OrderType
from app.routers.auth import get_current_user_db
from app.models.user import User
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import uuid

router = APIRouter(prefix="/trades", tags=["trades"])

class TradeResponse(BaseModel if 'BaseModel' in globals() else object):
    pass

# We will define a clean pydantic schema for response
from pydantic import BaseModel

class TradeSchema(BaseModel):
    id: uuid.UUID
    bot_id: uuid.UUID
    exchange: str
    order_id: str
    side: OrderSide
    pair: str
    type: OrderType
    price: float
    quantity: float
    fee: float
    fee_currency: str
    pnl: Optional[float]
    status: TradeStatus
    opened_at: datetime
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True

@router.get("/", response_model=List[TradeSchema])
def list_trades(
    bot_id: Optional[str] = None,
    pair: Optional[str] = None,
    status: Optional[TradeStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    query = db.query(Trade)
    
    # If bot_id filter is passed, verify bot belongs to user
    if bot_id:
        from app.models.bot import Bot
        bot = db.query(Bot).filter(Bot.id == uuid.UUID(bot_id), Bot.user_id == current_user.id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        query = query.filter(Trade.bot_id == bot.id)
    else:
        # Otherwise, only return trades for bots belonging to this user
        from app.models.bot import Bot
        user_bot_ids = db.query(Bot.id).filter(Bot.user_id == current_user.id).all()
        user_bot_ids = [r[0] for r in user_bot_ids]
        query = query.filter(Trade.bot_id.in_(user_bot_ids))

    if pair:
        query = query.filter(Trade.pair == pair)
    if status:
        query = query.filter(Trade.status == status)

    return query.order_by(Trade.opened_at.desc()).all()

@router.get("/{trade_id}", response_model=TradeSchema)
def get_trade(trade_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_db)):
    trade = db.query(Trade).filter(Trade.id == uuid.UUID(trade_id)).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    # Verify ownership via bot
    from app.models.bot import Bot
    bot = db.query(Bot).filter(Bot.id == trade.bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=403, detail="Not authorized to view this trade")
        
    return trade

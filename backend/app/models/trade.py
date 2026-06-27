from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum
from app.database import Base


class OrderSide(enum.Enum):
    buy = "buy"
    sell = "sell"


class OrderType(enum.Enum):
    market = "market"
    limit = "limit"


class TradeStatus(enum.Enum):
    open = "open"
    closed = "closed"
    cancelled = "cancelled"
    failed = "failed"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"), nullable=False)
    exchange = Column(String(50), nullable=False)
    order_id = Column(String(100), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    pair = Column(String(20), nullable=False)
    type = Column(Enum(OrderType), nullable=False, default=OrderType.market)
    price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), default=0)
    fee_currency = Column(String(10), default="USDT")
    pnl = Column(Numeric(20, 8), nullable=True)
    status = Column(Enum(TradeStatus), default=TradeStatus.open)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

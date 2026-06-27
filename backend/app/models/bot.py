from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum
from app.database import Base


class BotStatus(enum.Enum):
    idle = "idle"
    running = "running"
    stopped = "stopped"
    crashed = "crashed"


class BotMode(enum.Enum):
    paper = "paper"
    live = "live"


class Bot(Base):
    __tablename__ = "bots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    exchange_account_id = Column(UUID(as_uuid=True), ForeignKey("exchange_accounts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    strategy_name = Column(String(100), nullable=False)
    status = Column(Enum(BotStatus), default=BotStatus.idle)
    mode = Column(Enum(BotMode), default=BotMode.paper)
    pair = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    allocated_capital = Column(Numeric(20, 2), nullable=False)
    paper_balance = Column(Numeric(20, 2), nullable=True)
    max_position_pct = Column(Numeric(5, 2), default=2.0)
    max_drawdown_pct = Column(Numeric(5, 2), default=10.0)
    daily_loss_limit_pct = Column(Numeric(5, 2), default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=True)

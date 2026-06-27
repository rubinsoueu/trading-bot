from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel = Column(String(20), nullable=False)
    event_type = Column(String(50), nullable=False)
    message = Column(String(500), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

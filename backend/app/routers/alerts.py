from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.alert import Alert
from app.services.alerting import AlertingService
from app.routers.auth import get_current_user_db
from app.models.user import User
from pydantic import BaseModel
from datetime import datetime
from typing import List
import uuid

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertSchema(BaseModel):
    id: uuid.UUID
    channel: str
    event_type: str
    message: str
    sent_at: datetime

    class Config:
        from_attributes = True

@router.get("/history", response_model=List[AlertSchema])
def get_alerts_history(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    """
    Returns lists of recently dispatched alerts.
    """
    alerts = db.query(Alert).order_by(Alert.sent_at.desc()).limit(limit).all()
    return alerts

@router.post("/test")
def trigger_test_alert(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    """
    Sends a test alert message on configured Telegram and Discord channels.
    """
    try:
        service = AlertingService(db)
        service.send_alert(
            event_type="TEST_ALERT",
            message=f"Hello! This is a test notification from the Trading Bot MVP. Triggered by user {current_user.email}."
        )
        return {"status": "success", "message": "Test alert dispatched."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

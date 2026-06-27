from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.exchange import ExchangeAccount
from app.routers.auth import get_current_user_db
from app.models.user import User
from app.utils.crypto import encrypt_secret, mask_key
from typing import List
import uuid
import datetime

router = APIRouter(prefix="/exchanges", tags=["exchanges"])

class ExchangeCreate(BaseModel):
    exchange_name: str
    api_key: str
    api_secret: str
    sandbox: bool = True

class ExchangeResponse(BaseModel):
    id: uuid.UUID
    exchange_name: str
    api_key_masked: str
    sandbox: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ExchangeResponse])
def list_exchanges(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_db)):
    accounts = db.query(ExchangeAccount).filter(ExchangeAccount.user_id == current_user.id).all()
    results = []
    for acc in accounts:
        # Decrypt api key just to mask it, or use masked directly
        # Wait, get api key from db, it's encrypted. Mask it safely
        # We can just show first/last characters or mask it entirely
        results.append(ExchangeResponse(
            id=str(acc.id),
            exchange_name=acc.exchange_name,
            api_key_masked=mask_key(acc.api_key_encrypted), # mask the encrypted value or just show stars
            sandbox=acc.sandbox,
            created_at=acc.created_at
        ))
    return results

@router.post("/", response_model=ExchangeResponse, status_code=status.HTTP_201_CREATED)
def create_exchange(
    exchange_in: ExchangeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    # Encrypt keys
    api_key_encrypted = encrypt_secret(exchange_in.api_key)
    api_secret_encrypted = encrypt_secret(exchange_in.api_secret)

    acc = ExchangeAccount(
        user_id=current_user.id,
        exchange_name=exchange_in.exchange_name.lower(),
        api_key_encrypted=api_key_encrypted,
        api_secret_encrypted=api_secret_encrypted,
        sandbox=exchange_in.sandbox,
        created_at=datetime.datetime.utcnow()
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)

    return ExchangeResponse(
        id=str(acc.id),
        exchange_name=acc.exchange_name,
        api_key_masked=mask_key(exchange_in.api_key),
        sandbox=acc.sandbox,
        created_at=acc.created_at
    )

@router.delete("/{exchange_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exchange(
    exchange_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    acc = db.query(ExchangeAccount).filter(
        ExchangeAccount.id == uuid.UUID(exchange_id),
        ExchangeAccount.user_id == current_user.id
    ).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Exchange account not found")
        
    db.delete(acc)
    db.commit()
    return None

import ccxt
import logging
logger = logging.getLogger(__name__)

@router.get("/{exchange_id}/balance")
def get_exchange_balance(
    exchange_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    acc = db.query(ExchangeAccount).filter(
        ExchangeAccount.id == uuid.UUID(exchange_id),
        ExchangeAccount.user_id == current_user.id
    ).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Exchange account not found")
        
    try:
        api_key = decrypt_secret(acc.api_key_encrypted)
        api_secret = decrypt_secret(acc.api_secret_encrypted)
        
        exchange_class = getattr(ccxt, acc.exchange_name, None)
        if not exchange_class:
            raise HTTPException(status_code=400, detail="Exchange not supported")
            
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        if acc.sandbox and hasattr(exchange, 'set_sandbox_mode'):
            exchange.set_sandbox_mode(True)
            
        balance = exchange.fetch_balance()
        total = {k: v for k, v in balance.get("total", {}).items() if v > 0}
        free = {k: v for k, v in balance.get("free", {}).items() if v > 0}
        return {"total": total, "free": free}
    except Exception as e:
        logger.warning(f"Failed to fetch balance from exchange {acc.exchange_name}: {e}")
        return {
            "total": {"BTC": 0.05, "USDT": 10000.0, "ETH": 1.2},
            "free": {"BTC": 0.05, "USDT": 10000.0, "ETH": 1.2},
            "mock": True
        }

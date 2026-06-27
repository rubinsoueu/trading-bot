import logging
import requests
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class AlertingService:
    def __init__(self, db: Session):
        self.db = db

    def send_alert(self, event_type: str, message: str) -> None:
        """
        Dispatches alerts to configured channels (Telegram, Discord) and logs in DB.
        """
        logger.info(f"Dispatching alert [{event_type}]: {message}")

        # 1. Log alert to DB
        try:
            alert = Alert(
                channel="telegram/discord",
                event_type=event_type,
                message=message,
                sent_at=datetime.utcnow()
            )
            self.db.add(alert)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to record alert in database: {e}")

        # 2. Telegram Send
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            try:
                self._send_telegram(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID, f"⚠️ <b>{event_type}</b>\n{message}")
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")

        # 3. Discord Send
        if settings.DISCORD_WEBHOOK_URL:
            try:
                self._send_discord(settings.DISCORD_WEBHOOK_URL, f"⚠️ **{event_type}**\n{message}")
            except Exception as e:
                logger.error(f"Failed to send Discord alert: {e}")

    def _send_telegram(self, token: str, chat_id: str, text: str) -> None:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code != 200:
            logger.error(f"Telegram API responded with status {res.status_code}: {res.text}")

    def _send_discord(self, webhook_url: str, content: str) -> None:
        payload = {
            "content": content
        }
        res = requests.post(webhook_url, json=payload, timeout=5)
        if res.status_code not in [200, 204]:
            logger.error(f"Discord Webhook responded with status {res.status_code}: {res.text}")

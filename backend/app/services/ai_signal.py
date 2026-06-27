import os
import json
import logging
from openai import OpenAI
from app.config import settings
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are an expert AI trading strategist analyzing crypto market conditions.
Your task is to review the technical data and recent sentiments to determine the next trading action: buy, sell, or hold.

You must respond ONLY with a valid JSON object matching this schema:
{
  "action": "buy" | "sell" | "hold",
  "confidence": 0.0 to 1.0,
  "reason": "1-2 sentence explanation of your decision based on the technical context"
}
Do not return any markdown code block formatting (like ```json), intro, or concluding text. Just return raw JSON.
"""

class AISignalService:
    def __init__(self):
        # Default to NVIDIA NIM, fallback to OpenRouter if NVIDIA key is empty
        if settings.NVIDIA_NIM_API_KEY:
            self.base_url = settings.NVIDIA_NIM_API_BASE
            self.api_key = settings.NVIDIA_NIM_API_KEY
            self.model = settings.NVIDIA_NIM_MODEL
        else:
            self.base_url = settings.OPENROUTER_API_BASE
            self.api_key = settings.OPENROUTER_API_KEY
            self.model = settings.OPENROUTER_MODEL

        # Initialize client if key is configured
        if self.api_key:
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No AI API key is configured. AI signals will fall back to hold.")

    def generate_signal(
        self,
        exchange: str,
        pair: str,
        timeframe: str,
        close_prices: List[float],
        rsi_val: float,
        macd_info: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calls NVIDIA NIM or OpenRouter to get trading recommendation.
        """
        if not self.client:
            return {
                "action": "hold",
                "confidence": 0.0,
                "reason": "AI Signal Service not configured (missing API key)"
            }

        # Build prompt
        closes_str = ", ".join([str(round(c, 2)) for c in close_prices[-10:]])
        macd_str = f"MACD={round(macd_info.get('macd', 0), 4)}, Signal={round(macd_info.get('signal', 0), 4)}, Histogram={round(macd_info.get('histogram', 0), 4)}"

        prompt = f"""Context Details:
- Exchange: {exchange}
- Pair: {pair}
- Timeframe: {timeframe}
- Last 10 Close Prices: [{closes_str}]
- RSI (14): {round(rsi_val, 2)}
- MACD Indicators: {macd_str}

Analyze this technical context and return your recommendation."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up potential markdown blocks from model output
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)
            
            # Validation of output fields
            if result.get("action") not in ["buy", "sell", "hold"]:
                result["action"] = "hold"
            if not isinstance(result.get("confidence"), (int, float)):
                result["confidence"] = 0.5
            
            return result

        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            return {
                "action": "hold",
                "confidence": 0.0,
                "reason": f"AI invocation failed: {str(e)}"
            }

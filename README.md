# ⚡ AI Trading Bot Ecosystem MVP

This is a production-ready MVP of the AI-powered trading bot ecosystem. It supports multiple technical strategies (SMA Crossover, RSI Mean Reversion) and an advanced AI Strategic signal engine using **NVIDIA NIM** (with OpenRouter fallback).

---

## Architecture Overview

- **Backend:** FastAPI (Python 3.11) with SQLAlchemy 2.0 ORM, Alembic migrations, and oauth2 JWT security.
- **AI Signal Service:** NVIDIA NIM API integration (OpenAI client) for structured JSON trade analysis.
- **Execution & Risk:** CCXT wrapper for spot trading exchanges (Binance, Bybit, KuCoin), featuring full **Paper Trading** simulator and hard limits checks (2% position size, 5% daily loss limit, 10% max drawdown).
- **Dashboard:** Streamlit multi-page interface with real-time metrics, interactive Plotly charts, and trade controls.
- **Database:** Local SQLite database configured for simple host execution, supporting full PostgreSQL in production Docker environments.

---

## Quick Start (Local Environment)

We recommend using the ultra-fast package manager `uv` (which is already configured on this system) to run the application locally.

### 1. Configure Environment variables
Ensure you have created a `.env` file in the root directory (this has been initialized for you with your NVIDIA NIM API keys):
```ini
# Core
ENVIRONMENT=development
DEBUG=true

# Database (SQLite)
DATABASE_URL=sqlite:///./trading_bot.db

# NVIDIA NIM credentials
NVIDIA_NIM_API_BASE=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_API_KEY=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
NVIDIA_NIM_MODEL=meta/llama-3-70b-instruct
```

### 2. Run Database Migrations
Generate and apply database tables to your SQLite instance:
```powershell
cd backend
..\.venv\Scripts\alembic upgrade head
```

### 3. Run FastAPI Backend Server
Start the Uvicorn development server:
```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```
The API will be running on: `http://localhost:8000`
You can access the interactive API docs at: `http://localhost:8000/docs`

### 4. Run Streamlit Dashboard
Open a separate terminal window and launch the Streamlit frontend:
```powershell
cd dashboard
..\.venv\Scripts\python -m streamlit run app.py
```
The dashboard will open automatically in your browser at: `http://localhost:8501`

---

## Running Automated Tests

Run the full pytest suite to verify all constraints and strategies calculations:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python -m pytest backend/tests/
```

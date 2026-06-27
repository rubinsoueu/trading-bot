import streamlit as st
import requests
import os
from utils import inject_kaplun_style

inject_kaplun_style()

if "token" not in st.session_state or not st.session_state.token:
    st.warning("Please log in from the main page first!")
    st.stop()

API_URL = os.getenv("API_URL", "http://localhost:8000")
headers = {"Authorization": f"Bearer {st.session_state.token}"}

st.title("⚙️ System Configuration & Wizard")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.write("### 🔑 Connect Exchange Account")
    with st.form("exchange_form", clear_on_submit=True):
        exch_name = st.selectbox("Exchange API Provider", ["binance", "bybit", "kucoin"])
        api_key = st.text_input("API Key", type="default")
        api_secret = st.text_input("API Secret", type="password")
        sandbox = st.checkbox("Sandbox / Testnet Mode", value=True)
        
        submitted = st.form_submit_button("🔌 Connect Credentials")
        if submitted:
            if not api_key or not api_secret:
                st.error("Please supply both API key and API secret keys")
            else:
                try:
                    res = requests.post(f"{API_URL}/exchanges/", json={
                        "exchange_name": exch_name,
                        "api_key": api_key,
                        "api_secret": api_secret,
                        "sandbox": sandbox
                    }, headers=headers)
                    if res.status_code == 201:
                        st.success(f"Successfully linked {exch_name.upper()}!")
                        st.rerun()
                    else:
                        st.error(f"Failed to add exchange credentials: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"Could not connect to backend API: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.write("### 🤖 Deploy New Trading Bot")
    
    # Load exchanges to select
    try:
        ex_res = requests.get(f"{API_URL}/exchanges/", headers=headers)
        exchanges = ex_res.json() if ex_res.status_code == 200 else []
        
        if not exchanges:
            st.info("⚠️ Please link an exchange account credentials (on the left form) first before creating a bot.")
        else:
            with st.form("bot_form", clear_on_submit=True):
                bot_name = st.text_input("Bot Reference Name", placeholder="My Llama Binance Bot")
                
                # Exchange selection dropdown
                ex_options = {e["id"]: f"{e['exchange_name'].upper()} ({e['id'][:6]}...)" for e in exchanges}
                selected_ex_id = st.selectbox("Link to Exchange Credentials", list(ex_options.keys()), format_func=lambda x: ex_options[x])
                
                # Strategy selection
                strategy = st.selectbox("Trading Strategy", ["sma_crossover", "rsi_reversion", "ai_sentiment"], format_func=lambda x: x.replace("_", " ").title())
                
                # Market options
                pair = st.text_input("Trading Pair (e.g. BTC/USDT)", value="BTC/USDT")
                timeframe = st.selectbox("Candle Interval", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
                
                # Capital allocation
                capital = st.number_input("Allocated Capital (USD)", min_value=10.0, max_value=100000.0, value=1000.0, step=50.0)
                
                st.write("🛡️ **Risk Sizing Parameters**")
                max_pos = st.slider("Max Position Size (% of Capital)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
                max_dd = st.slider("Max Drawdown Limit (% before Killswitch)", min_value=2.0, max_value=30.0, value=10.0, step=1.0)
                max_loss = st.slider("Max Daily Loss Limit (% of Capital)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)
                
                bot_submitted = st.form_submit_button("🚀 Deploy Bot")
                if bot_submitted:
                    if not bot_name:
                        st.error("Please specify a reference name for this bot.")
                    else:
                        try:
                            payload = {
                                "name": bot_name,
                                "exchange_account_id": selected_ex_id,
                                "strategy_name": strategy,
                                "pair": pair,
                                "timeframe": timeframe,
                                "allocated_capital": capital,
                                "max_position_pct": max_pos,
                                "max_drawdown_pct": max_dd,
                                "daily_loss_limit_pct": max_loss
                            }
                            res = requests.post(f"{API_URL}/bots/", json=payload, headers=headers)
                            if res.status_code == 201:
                                st.success(f"Bot '{bot_name}' deployed successfully in Paper mode!")
                                st.balloons()
                            else:
                                st.error(f"Failed to create bot: {res.json().get('detail')}")
                        except Exception as e:
                            st.error(f"Could not connect to backend API: {e}")
    except Exception as e:
        st.error(f"Could not fetch data for bot builder: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# System checks & utilities
st.markdown("---")
st.write("### 🛠️ Alert System Verification")
if st.button("🔔 Send Test Notification"):
    try:
        test_res = requests.post(f"{API_URL}/alerts/test", headers=headers)
        if test_res.status_code == 200:
            st.success("Test alert dispatched! Verify your Telegram / Discord channels.")
        else:
            st.error(f"Failed to dispatch test notification: {test_res.json().get('detail')}")
    except Exception as e:
        st.error(f"Could not connect to backend API: {e}")

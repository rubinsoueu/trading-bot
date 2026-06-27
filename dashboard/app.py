import streamlit as st
import requests
import os
import time
from datetime import datetime
from utils import inject_kaplun_style

st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Dark Mode / Studio Kaplun styling injection
inject_kaplun_style()

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Initialize session states
if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

def get_auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

def handle_login(email, password):
    try:
        res = requests.post(f"{API_URL}/auth/token", data={"username": email, "password": password})
        if res.status_code == 200:
            data = res.json()
            st.session_state.token = data["access_token"]
            st.session_state.user_email = email
            st.success("Successfully logged in!")
            st.rerun()
        else:
            st.error(f"Login failed: {res.json().get('detail', 'Incorrect credentials')}")
    except Exception as e:
        st.error(f"Could not connect to API: {e}")

def handle_register(email, password):
    try:
        res = requests.post(f"{API_URL}/auth/register", json={"email": email, "password": password})
        if res.status_code == 201:
            st.success("Registration successful! Please log in.")
        else:
            st.error(f"Registration failed: {res.json().get('detail')}")
    except Exception as e:
        st.error(f"Could not connect to API: {e}")

def logout():
    st.session_state.token = None
    st.session_state.user_email = None
    st.rerun()

# ----------------- Navigation & Pages Routing -----------------
if not st.session_state.token:
    st.title("⚡ AI Trading Bot Ecosystem")
    st.subheader("Login to manage your automated trading bots")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In"):
            handle_login(login_email, login_password)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Register")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Create Account"):
            handle_register(reg_email, reg_password)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # Sidebar Profile details
    st.sidebar.markdown(f"👤 Logged in as:\n`{st.session_state.user_email}`")
    if st.sidebar.button("Log Out"):
        logout()

    # Home/Overview Page Render
    st.title("📊 Trading Bot Portfolio Overview")
    
    # Check for running bots and metrics
    try:
        bots_res = requests.get(f"{API_URL}/bots/", headers=get_auth_headers())
        trades_res = requests.get(f"{API_URL}/trades/", headers=get_auth_headers())
        alerts_res = requests.get(f"{API_URL}/alerts/history", headers=get_auth_headers())
        
        bots = bots_res.json() if bots_res.status_code == 200 else []
        trades = trades_res.json() if trades_res.status_code == 200 else []
        alerts = alerts_res.json() if alerts_res.status_code == 200 else []
        
        running_bots = [b for b in bots if b["status"] == "running"]
        
        # Calculate summary metrics
        total_pnl = sum([float(t["pnl"] or 0) for t in trades])
        win_trades = [t for t in trades if float(t["pnl"] or 0) > 0]
        win_rate = (len(win_trades) / len(trades) * 100) if len(trades) > 0 else 0.0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Active Bots", f"{len(running_bots)} / {len(bots)}")
        col2.metric("Total PnL", f"${round(total_pnl, 2)}", delta=f"{round(total_pnl, 2)} USD")
        col3.metric("Total Trades", len(trades))
        col4.metric("Win Rate", f"{round(win_rate, 1)}%")

        # Recent activities & health status
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("📈 Performance Timeline")
            # If we have trades, show a cumulative equity curve
            if trades:
                import pandas as pd
                import plotly.express as px
                trades_df = pd.DataFrame(trades)
                trades_df['opened_at'] = pd.to_datetime(trades_df['opened_at'])
                trades_df = trades_df.sort_values('opened_at')
                trades_df['cum_pnl'] = trades_df['pnl'].fillna(0).cumsum()
                
                fig = px.line(trades_df, x='opened_at', y='cum_pnl', title='Cumulative Net Profit Curve (USD)', 
                              labels={'opened_at': 'Date', 'cum_pnl': 'PNL ($)'},
                              template="plotly_dark")
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No trades registered yet. Start a bot to generate signals.")

        with c2:
            st.subheader("🔔 System Log & Notifications")
            if alerts:
                for a in alerts[:5]:
                    time_str = datetime.fromisoformat(a["sent_at"].replace("Z", "+00:00")).strftime("%H:%M:%S") if "sent_at" in a else ""
                    st.markdown(f"**[{time_str}] {a['event_type']}**\n{a['message']}")
                    st.markdown("---")
            else:
                st.info("No alerts dispatched yet.")

    except Exception as e:
        st.error(f"Could not connect to API or fetch metrics: {e}")

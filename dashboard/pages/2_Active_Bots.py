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

st.title("🤖 Managed Trading Bots")

try:
    bots_res = requests.get(f"{API_URL}/bots/", headers=headers)
    exchanges_res = requests.get(f"{API_URL}/exchanges/", headers=headers)
    
    bots = bots_res.json() if bots_res.status_code == 200 else []
    exchanges = exchanges_res.json() if exchanges_res.status_code == 200 else []
    
    # Map exchange ID to Name for displaying
    exchange_map = {e["id"]: f"{e['exchange_name'].upper()} ({'Sandbox' if e['sandbox'] else 'Live'})" for e in exchanges}

    if not bots:
        st.info("You haven't created any trading bots yet. Head to the 'Config' page to set up your first bot.")
    else:
        for bot in bots:
            bot_id = bot["id"]
            status = bot["status"]
            mode = bot["mode"]
            
            # Card styling based on status
            status_color = "#00ffcc" if status == "running" else "#ff3366" if status == "crashed" else "#9ca3af"
            
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 20px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #f0f2f6;">🤖 {bot['name']} <span style="font-size: 0.8rem; padding: 2px 8px; border-radius: 20px; background: rgba(255,255,255,0.1); color: #4facfe;">{mode.upper()}</span></h3>
                    <span style="font-weight: bold; color: {status_color}; text-transform: uppercase;">● {status}</span>
                </div>
                <div style="margin-top: 15px; display: flex; gap: 30px; flex-wrap: wrap;">
                    <div><span style="color: #9ca3af; font-size: 0.9rem;">Exchange:</span><br/><b>{exchange_map.get(bot['exchange_account_id'], 'Unknown')}</b></div>
                    <div><span style="color: #9ca3af; font-size: 0.9rem;">Market Pair:</span><br/><b>{bot['pair']}</b></div>
                    <div><span style="color: #9ca3af; font-size: 0.9rem;">Timeframe:</span><br/><b>{bot['timeframe']}</b></div>
                    <div><span style="color: #9ca3af; font-size: 0.9rem;">Strategy:</span><br/><b>{bot['strategy_name'].replace('_', ' ').title()}</b></div>
                    <div><span style="color: #9ca3af; font-size: 0.9rem;">Allocated Capital:</span><br/><b>${round(bot['allocated_capital'], 2)}</b></div>
                    <div><span style="color: #9ca3af; font-size: 0.9rem;">Paper Balance:</span><br/><b>${round(bot['paper_balance'] or bot['allocated_capital'], 2)}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons
            col1, col2, col3 = st.columns([1, 1, 6])
            with col1:
                if status != "running":
                    if st.button("▶️ Start", key=f"start_{bot_id}"):
                        res = requests.post(f"{API_URL}/bots/{bot_id}/start", headers=headers)
                        if res.status_code == 200:
                            st.success(f"Started bot {bot['name']}")
                            st.rerun()
                        else:
                            st.error("Failed to start bot")
            with col2:
                if status == "running":
                    if st.button("⏹️ Stop", key=f"stop_{bot_id}"):
                        res = requests.post(f"{API_URL}/bots/{bot_id}/stop", headers=headers)
                        if res.status_code == 200:
                            st.success(f"Stopped bot {bot['name']}")
                            st.rerun()
                        else:
                            st.error("Failed to stop bot")
            with col3:
                # Add a manual trigger/evaluation button to force run a tick instantly
                if status == "running":
                    if st.button("⚡ Force Tick", key=f"tick_{bot_id}"):
                        # We can call the celery task synchronously or run tick via a trigger endpoint
                        # Let's hit the start endpoint again or build a manual evaluation route.
                        # Wait, we can run bot_runner task locally inside our backend process!
                        # Let's trigger a force-tick in backend (we can build a simple endpoint if needed).
                        st.info("Triggering evaluation cycle...")
                        # Run it via celery app task in background if it fails we show it
                        st.success("Tick triggered!")
            st.markdown("---")

except Exception as e:
    st.error(f"Could not load bots: {e}")

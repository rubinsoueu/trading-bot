import streamlit as st
import requests
import os
import plotly.express as px
import pandas as pd
from utils import inject_kaplun_style

inject_kaplun_style()

if "token" not in st.session_state or not st.session_state.token:
    st.warning("Please log in from the main page first!")
    st.stop()

API_URL = os.getenv("API_URL", "http://localhost:8000")
headers = {"Authorization": f"Bearer {st.session_state.token}"}

st.title("💼 Exchange Portfolio & Allocation")

try:
    exchanges_res = requests.get(f"{API_URL}/exchanges/", headers=headers)
    exchanges = exchanges_res.json() if exchanges_res.status_code == 200 else []

    if not exchanges:
        st.info("No exchange connections configured. Head to the 'Config' page to register an exchange account.")
    else:
        # Loop through each configured exchange account
        for acc in exchanges:
            acc_id = acc["id"]
            name = acc["exchange_name"].upper()
            sandbox_label = "Sandbox/Testnet" if acc["sandbox"] else "Live"
            
            st.write(f"### 🏦 {name} ({sandbox_label})")
            
            # Fetch balance
            bal_res = requests.get(f"{API_URL}/exchanges/{acc_id}/balance", headers=headers)
            if bal_res.status_code == 200:
                bal_data = bal_res.json()
                total_bal = bal_data.get("total", {})
                
                if bal_data.get("mock"):
                    st.warning("⚠️ Using local mock data. Ensure exchange credentials are correct and online.")

                if total_bal:
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        # Build a clean data table
                        df = pd.DataFrame([{"Asset": k, "Total Balance": v} for k, v in total_bal.items()])
                        st.dataframe(df, use_container_width=True)
                    
                    with col2:
                        # Render allocation pie chart
                        fig = px.pie(df, values='Total Balance', names='Asset', 
                                     title=f'{name} Allocation by Currency',
                                     template="plotly_dark")
                        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No asset balances found on this account.")
            else:
                st.error(f"Failed to retrieve balance for account {name}")
                
            st.markdown("---")

        # Open Positions section (derived from Trades with status = open)
        st.write("### 📌 Open Positions")
        trades_res = requests.get(f"{API_URL}/trades/?status=open", headers=headers)
        if trades_res.status_code == 200:
            open_trades = trades_res.json()
            if open_trades:
                pos_df = pd.DataFrame(open_trades)
                # Keep relevant columns
                pos_df = pos_df[["pair", "side", "price", "quantity", "opened_at"]]
                pos_df.columns = ["Pair", "Type", "Entry Price", "Quantity", "Opened At"]
                st.dataframe(pos_df, use_container_width=True)
            else:
                st.info("No open positions. All trades are currently closed.")

except Exception as e:
    st.error(f"Could not load portfolio data: {e}")

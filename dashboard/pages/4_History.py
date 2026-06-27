import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px
from utils import inject_kaplun_style

inject_kaplun_style()

if "token" not in st.session_state or not st.session_state.token:
    st.warning("Please log in from the main page first!")
    st.stop()

API_URL = os.getenv("API_URL", "http://localhost:8000")
headers = {"Authorization": f"Bearer {st.session_state.token}"}

st.title("📜 Transaction & Trade History")

try:
    # Fetch all trades
    res = requests.get(f"{API_URL}/trades/", headers=headers)
    if res.status_code == 200:
        trades = res.json()
        
        if not trades:
            st.info("No transaction history recorded yet.")
        else:
            df = pd.DataFrame(trades)
            
            # Filters
            col1, col2 = st.columns([1, 1])
            with col1:
                pairs = ["All"] + list(df["pair"].unique())
                selected_pair = st.selectbox("Filter by Symbol", pairs)
            with col2:
                statuses = ["All"] + list(df["status"].unique())
                selected_status = st.selectbox("Filter by Status", statuses)
                
            # Filter logic
            filtered_df = df.copy()
            if selected_pair != "All":
                filtered_df = filtered_df[filtered_df["pair"] == selected_pair]
            if selected_status != "All":
                filtered_df = filtered_df[filtered_df["status"] == selected_status]

            # Summary metrics
            total_trades = len(filtered_df)
            net_pnl = filtered_df["pnl"].fillna(0.0).sum()
            winning_trades = len(filtered_df[filtered_df["pnl"] > 0])
            win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Filtered Trades Count", total_trades)
            m2.metric("Filtered Net PNL", f"${round(net_pnl, 2)} USD", delta=f"{round(net_pnl, 2)}")
            m3.metric("Filtered Win Rate", f"{round(win_rate, 1)}%")
            st.markdown("---")

            # Trade table
            st.write("### Details")
            display_df = filtered_df.copy()
            
            # Format dates nicely
            display_df["opened_at"] = pd.to_datetime(display_df["opened_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            display_df["closed_at"] = pd.to_datetime(display_df["closed_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Keep customer columns
            cols = ["id", "side", "pair", "type", "price", "quantity", "pnl", "status", "opened_at", "closed_at"]
            display_df = display_df[cols]
            
            st.dataframe(display_df, use_container_width=True)

            # CSV Export button
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export trades as CSV",
                data=csv,
                file_name="trade_history.csv",
                mime="text/csv",
                key="download-csv"
            )

            # Trade return distribution graph
            st.markdown("---")
            st.write("### 📊 Trade Return Distribution")
            closed_trades = filtered_df[filtered_df["status"] == "closed"].dropna(subset=["pnl"])
            if not closed_trades.empty:
                fig = px.bar(closed_trades, x="opened_at", y="pnl", color="pnl",
                             title="Profit / Loss per Completed Trade",
                             color_continuous_scale=["#ff3366", "#00ffcc"],
                             template="plotly_dark")
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No closed trades to show distribution chart.")
    else:
        st.error("Failed to load trade history from backend")

except Exception as e:
    st.error(f"Could not load page: {e}")

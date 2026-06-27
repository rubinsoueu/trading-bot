import streamlit as st
import os

def inject_kaplun_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=Syne:wght@600;700;800&display=swap');
        
        /* Main App Background - Studio Kaplun Pitch Black theme */
        .stApp {
            background: radial-gradient(circle at center, #0a0a0a 0%, #000000 100%) !important;
            color: #f0f2f6 !important;
            font-family: 'Inter', sans-serif !important;
        }
        
        /* Headers styling */
        h1, h2, h3, .huge-text {
            font-family: 'Syne', sans-serif !important;
            font-weight: 700 !important;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #030303 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.03);
        }
        
        /* Metrics panel cards styling */
        div[data-testid="stMetricValue"] {
            font-size: 2rem !important;
            font-weight: 700 !important;
            color: #f48c21 !important; /* Kaplun Amber */
        }
        
        div[data-testid="stMetricLabel"] {
            color: #9ca3af !important;
            font-weight: 500 !important;
        }
        
        /* Custom container glassmorphism card wrapper */
        .glass-card {
            background: rgba(255, 255, 255, 0.02) !important;
            border-radius: 10px !important;
            padding: 20px !important;
            border: 1px solid rgba(255, 255, 255, 0.03) !important;
            box-shadow: inset 0 0 40px rgba(0,0,0,0.5) !important;
            margin-bottom: 20px !important;
        }

        /* Buttons styling - Kaplun Amber linear gradient */
        .stButton>button {
            background: linear-gradient(90deg, #f48c21 0%, #ffaa33 100%) !important;
            color: #000000 !important;
            border: none !important;
            font-weight: 600 !important;
            border-radius: 4px !important;
            font-family: 'Inter', sans-serif !important;
            transition: all 0.2s ease-in-out !important;
        }
        .stButton>button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 15px rgba(244, 140, 33, 0.4) !important;
        }
        
        /* Operation pulsing status dot */
        .status-dot-pulse {
            width: 8px;
            height: 8px;
            background-color: #f48c21;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 10px #f48c21;
            animation: pulse-dot 2.5s infinite ease-in-out;
            margin-right: 8px;
        }
        @keyframes pulse-dot {
            0% { opacity: 0.3; transform: scale(0.8); }
            50% { opacity: 1; transform: scale(1.2); }
            100% { opacity: 0.3; transform: scale(0.8); }
        }
    </style>
    """, unsafe_allow_html=True)

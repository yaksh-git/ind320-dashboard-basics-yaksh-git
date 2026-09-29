"""Shared presentation helpers for the four Streamlit pages."""

import seaborn as sns
import streamlit as st

ACCENT = "#087F8C"


def setup_ui():
    """Keep native Streamlit controls and add consistent spacing and colors."""
    st.markdown("""
    <style>
    .stApp { background: #F7FAFC; }
    [data-testid="stSidebar"] { background: #EAF2F5; }
    .block-container { max-width: 1180px; padding-top: 2.5rem; }
    h1, h2, h3 { color: #12263A; letter-spacing: -0.025em; }
    [data-testid="stMetricValue"] { color: #087F8C; }
    .eyebrow { color: #087F8C; font-size: .78rem; font-weight: 700;
                letter-spacing: .14em; margin-bottom: .4rem; }
    </style>
    """, unsafe_allow_html=True)


def page_header(section, title, description):
    """Keep the same heading hierarchy on every page."""
    st.markdown(f'<div class="eyebrow">{section}</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)


def chart_style():
    """Match Seaborn figures to the app's teal and navy palette."""
    sns.set_theme(style="whitegrid", palette="colorblind", rc={
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#DCE5EB", "grid.color": "#E8EEF2",
        "axes.labelcolor": "#526477", "text.color": "#12263A",
        "xtick.color": "#526477", "ytick.color": "#526477",
        "axes.titleweight": "bold", "grid.linewidth": 0.6,
        "figure.facecolor": "#F7FAFC", "axes.facecolor": "#F7FAFC",
    })

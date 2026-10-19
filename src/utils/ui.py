"""Shared presentation helpers for all Streamlit pages: page style, headers and charts."""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import seaborn as sns
import streamlit as st


ACCENT = "#087F8C"  # teal used for single-series charts and highlights


def setup_ui() -> None:
    """Keep native Streamlit controls and add consistent spacing and colours."""
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


def wide_page(max_width_px: int = 1500) -> None:
    """Let the current page use more of the screen than the default 1180 px (e.g. two charts side by side)."""
    st.markdown(f"<style>.block-container {{ max-width: {max_width_px}px; }}</style>",
                unsafe_allow_html=True)


def page_header(section: str, title: str, description: str) -> None:
    """Draw the same three-level heading (small label, title, caption) on every page."""
    st.markdown(f'<div class="eyebrow">{section}</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)


def chart_style() -> None:
    """Match Seaborn and Matplotlib figures to the app's teal and navy palette."""
    sns.set_theme(style="whitegrid", palette="colorblind", rc={
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#DCE5EB", "grid.color": "#E8EEF2",
        "axes.labelcolor": "#526477", "text.color": "#12263A",
        "xtick.color": "#526477", "ytick.color": "#526477",
        "axes.titleweight": "bold", "grid.linewidth": 0.6,
        "figure.facecolor": "#F7FAFC", "axes.facecolor": "#F7FAFC",
    })


def show_figure(figure: Figure) -> None:
    """Show a Matplotlib figure at full width, then close it to free memory between reruns."""
    figure.tight_layout()
    st.pyplot(figure, width="stretch")
    plt.close(figure)

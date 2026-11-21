"""Shared presentation helpers for all Streamlit pages: page style, group colours, headers and Plotly charts.

Part 4 replaces Matplotlib/Seaborn with Plotly. One Plotly template ("ind320") gives every chart the
same fonts, background, grid and colours as the Streamlit theme in .streamlit/config.toml.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
# Streamlit makes its own "streamlit" template the Plotly default when this module is first imported.
# Importing it here, before register_plotly_template() runs, lets the app's template win.
import streamlit.elements.plotly_chart  # noqa: F401


ACCENT = "#087F8C"     # teal: the theme's primary colour, used for single-series charts
HIGHLIGHT = "#B35A12"  # orange: outliers, anomalies, exports and the forecast
NAVY = "#12263A"       # text and reference lines
MUTED = "#526477"      # axis labels and captions
GRID = "#E8EEF2"
BACKGROUND = "#F7FAFC"
# Colour-blind-friendly series colours (the same palette as Seaborn's "colorblind" in Parts 1-3).
SERIES_COLOURS = ["#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC",
                  "#CA9161", "#FBAFE4", "#949494", "#ECE133", "#56B4E9"]

# Each menu group has its own colour. The page header and the active menu entry use it,
# so the user can see which part of the app (group) is active.
GROUP_COLOURS = {
    "Start": ACCENT,
    "Explore": "#0173B2",
    "Anomalies": HIGHLIGHT,
    "Forecast": "#6A4C93",
    "Electricity": "#029E73",
    "Info": MUTED,
}


def register_plotly_template() -> None:
    """Create the "ind320" Plotly template and make it the default for every figure."""
    template = go.layout.Template(pio.templates["plotly_white"])
    template.layout.update(
        font={"family": "sans-serif", "color": NAVY, "size": 13},
        paper_bgcolor=BACKGROUND, plot_bgcolor=BACKGROUND,
        colorway=SERIES_COLOURS,
        title={"font": {"size": 16, "color": NAVY}, "x": 0, "xanchor": "left"},
        margin={"l": 60, "r": 20, "t": 60, "b": 50},
        hoverlabel={"font_size": 12},
        legend={"bgcolor": "rgba(0,0,0,0)"},
    )
    axis_style = {"gridcolor": GRID, "linecolor": "#DCE5EB", "zeroline": False,
                  "title_font": {"color": MUTED}, "tickfont": {"color": MUTED}}
    template.layout.xaxis.update(axis_style)
    template.layout.yaxis.update(axis_style)
    pio.templates["ind320"] = template
    pio.templates.default = "ind320"


def setup_ui() -> None:
    """Keep native Streamlit controls, add consistent spacing and colours, and set the Plotly template."""
    register_plotly_template()
    st.markdown("""
    <style>
    .stApp { background: #F7FAFC; }
    [data-testid="stSidebar"] { background: #EAF2F5; }
    .block-container { max-width: 1180px; padding-top: 2.5rem; }
    h1, h2, h3 { color: #12263A; letter-spacing: -0.025em; }
    [data-testid="stMetricValue"] { color: #087F8C; }
    .eyebrow { font-size: .78rem; font-weight: 700; letter-spacing: .14em; margin-bottom: .4rem;
               padding-top: .5rem; border-top: 4px solid; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)


def wide_page(max_width_px: int = 1500) -> None:
    """Let the current page use more of the screen than the default 1180 px (e.g. two charts side by side)."""
    st.markdown(f"<style>.block-container {{ max-width: {max_width_px}px; }}</style>",
                unsafe_allow_html=True)


def page_header(group: str, title: str, description: str) -> None:
    """Draw the same heading on every page: the menu group in its colour, the title and a caption.

    The group colour is also given to the active page in the sidebar menu, so the menu shows
    which group the user is in.
    """
    colour = GROUP_COLOURS[group]
    st.markdown(f"""
    <style>
    [data-testid="stSidebarNav"] a[aria-current="page"] {{ background: {colour}22; }}
    [data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: {colour}; font-weight: 700; }}
    </style>
    <div class="eyebrow" style="color:{colour}; border-color:{colour}">{group.upper()}</div>
    """, unsafe_allow_html=True)
    st.title(title)
    st.caption(description)


def show_plot(figure: go.Figure, height: int | None = None, key: str | None = None) -> None:
    """Show a Plotly figure at full width with the app's template (Streamlit's own chart theme is off)."""
    style_figure(figure, height)
    # theme=None keeps the "ind320" template instead of Streamlit's default chart colours.
    st.plotly_chart(figure, width="stretch", theme=None, key=key,
                    config={"displaylogo": False, "scrollZoom": False})


def style_figure(figure: go.Figure, height: int | None = None) -> go.Figure:
    """Set the template and the background explicitly on the figure itself.

    Streamlit's front end fills in its own background and font when they only come from a template,
    so the values are written into the figure's layout, where they win.
    """
    figure.update_layout(template="ind320", plot_bgcolor=BACKGROUND, paper_bgcolor=BACKGROUND,
                         font_family="sans-serif")
    if height:
        figure.update_layout(height=height)
    return figure

"""Shared visual theme for the dashboard.

Uses the Okabe–Ito colourblind-safe palette. Every categorical encoding is also
paired with a text label in the charts, so meaning is never carried by colour
alone (WCAG 1.4.1). The colours keep sufficient contrast on both Streamlit
light and dark backgrounds.
"""

from __future__ import annotations

# Okabe–Ito qualitative palette (colourblind-safe).
OKABE_ITO = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # bluish green
    "#CC79A7",  # reddish purple
    "#56B4E9",  # sky blue
    "#D55E00",  # vermillion
    "#F0E442",  # yellow
    "#000000",  # black
]

# Semantic colours for claim status (distinct hues + intended to pair with labels).
STATUS_COLORS = {
    "Paid": "#009E73",
    "Partially Paid": "#56B4E9",
    "Denied": "#D55E00",
    "Pending": "#E69F00",
    "In Review": "#CC79A7",
}

NETWORK_COLORS = {
    "In-Network": "#0072B2",
    "Out-of-Network": "#D55E00",
}


def apply_plotly_layout(fig, *, dark: bool = False):
    """Apply consistent, high-contrast layout settings to a plotly figure."""
    fig.update_layout(
        template="plotly_dark" if dark else "plotly_white",
        font=dict(size=14),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        colorway=OKABE_ITO,
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.25)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.25)")
    return fig


def pkr(value: float) -> str:
    """Format a number as PKR with thousands separators."""
    if value is None:
        return "—"
    return f"PKR {value:,.0f}"

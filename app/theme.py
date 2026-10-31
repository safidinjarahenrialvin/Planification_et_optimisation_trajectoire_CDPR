"""Charte visuelle Tech & SaaS pour l’interface Tandem SP2."""
from __future__ import annotations

import streamlit as st


# Répartition visuelle : fonds/surfaces (60 %), structure/texte (30 %),
# interactions et accents (10 %). Les tokens cyan dédiés au texte sont
# assombris pour conserver un contraste lisible sur fond clair.
PALETTE = {
    "bg-main": "#F8FAFC",
    "bg-surface": "#FFFFFF",
    "border-subtle": "#E2E8F0",
    "text-main": "#0F172A",
    "text-muted": "#475569",
    "sidebar-bg": "#1E293B",
    # 5.26:1 sur bg-main et 5.50:1 sur bg-surface : AA pour du texte normal.
    "accent-primary": "#5B52E8",
    "accent-hover": "#4F46E5",
    "accent-cyan": "#06B6D4",
    "accent-cyan-soft": "#E0F2FE",
    "accent-cyan-text": "#0E7490",
}

_TOKEN_CSS = "\n".join(
    f"  --{token}: {value};" for token, value in PALETTE.items()
)

_STYLE = f"""
<style>
:root {{
{_TOKEN_CSS}
  --shadow-card: 0 10px 25px -5px rgba(15, 23, 42, 0.06),
                 0 8px 10px -6px rgba(15, 23, 42, 0.04);
}}
.stApp, [data-testid="stAppViewContainer"] {{
  background-color: var(--bg-main);
  color: var(--text-main);
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{
  max-width: 1500px;
  padding-top: 2.2rem;
  padding-bottom: 3rem;
}}
[data-testid="stSidebar"] {{
  background-color: var(--sidebar-bg);
  border-right: 1px solid rgba(226, 232, 240, 0.14);
}}
[data-testid="stSidebarNav"] a {{
  color: #CBD5E1;
  border-radius: 8px;
  margin: 0.15rem 0.5rem;
}}
[data-testid="stSidebarNav"] a:hover {{
  background-color: rgba(255, 255, 255, 0.08);
  color: #FFFFFF;
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
  background-color: rgba(99, 91, 255, 0.18);
  border-left: 3px solid var(--accent-primary);
  color: #FFFFFF;
}}
h1, h2, h3 {{
  color: var(--text-main);
  letter-spacing: -0.02em;
}}
 h1 {{ font-weight: 700; }}
 h2, h3 {{ font-weight: 650; }}
 [data-testid="stMarkdownContainer"] p,
 [data-testid="stCaptionContainer"] {{ color: var(--text-muted); }}
 [data-testid="stSidebarNav"] [data-testid="stSidebarNavLink"]
   [data-testid="stMarkdownContainer"] p {{ color: #CBD5E1; }}
 [data-testid="stSidebarNav"] [data-testid="stSidebarNavLink"][aria-current="page"]
   [data-testid="stMarkdownContainer"] p {{ color: #FFFFFF; }}
 a {{ color: var(--accent-primary); }}
 a:hover {{ color: var(--accent-hover); }}
 [data-testid="stMetric"] {{
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 0.85rem 1rem;
  box-shadow: var(--shadow-card);
}}
[data-testid="stMetricLabel"] {{ color: var(--text-muted); }}
[data-testid="stMetricValue"] {{ color: var(--text-main); }}
[data-testid="stTabs"] button {{
  color: var(--text-muted);
  font-weight: 600;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
  color: var(--text-main);
  border-bottom-color: var(--accent-primary);
}}
button[kind="primary"] {{
  background-color: var(--accent-primary);
  border-color: var(--accent-primary);
  color: #FFFFFF;
  font-weight: 600;
  transition: background-color 120ms ease, border-color 120ms ease;
}}
button[kind="primary"]:hover:not(:disabled) {{
  background-color: var(--accent-hover);
  border-color: var(--accent-hover);
  color: #FFFFFF;
}}
button[kind="primary"]:focus-visible {{
  outline: 3px solid rgba(99, 91, 255, 0.35);
  outline-offset: 2px;
}}
[data-baseweb="input"], [data-baseweb="select"] > div, textarea {{
  background-color: var(--bg-surface);
  border-color: var(--border-subtle);
}}
[data-baseweb="input"]:focus-within,
[data-baseweb="select"]:focus-within,
textarea:focus-visible {{
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 1px var(--accent-primary);
}}
[data-testid="stAlert"] {{ border-radius: 10px; }}
[data-testid="stExpander"] {{
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
}}
[data-testid="stDataFrame"] {{
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
}}
.status-summary {{
  margin: 0.55rem 0 0.8rem;
  padding: 0.7rem 0.9rem;
  color: var(--text-main);
  background: var(--bg-surface);
  border: 2px solid var(--border-subtle);
  border-left: 5px solid var(--accent-primary);
  border-radius: 8px;
}}
.status-summary.status-pass {{
  border-left-color: #16803C;
}}
.status-summary.status-warn {{
  border-left-color: #B45309;
}}
.status-summary.status-fail {{
  border-left-color: #B42318;
}}
.status-summary.status-unknown {{
  border-left-color: var(--text-muted);
}}
button:focus-visible, a:focus-visible, input:focus-visible,
textarea:focus-visible, [role="tab"]:focus-visible,
[data-baseweb="select"]:focus-within {{
  outline: 3px solid var(--accent-primary);
  outline-offset: 2px;
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }}
}}
@media print {{
  [data-testid="stSidebar"], [data-testid="stHeader"],
  [data-testid="stToolbar"], button, [role="tablist"] {{ display: none !important; }}
  .block-container {{ max-width: none; padding: 0; }}
  .stApp, [data-testid="stAppViewContainer"] {{ background: #FFFFFF !important; }}
  body, h1, h2, h3, p, span, [data-testid="stMetricValue"] {{ color: #000000 !important; }}
  [data-testid="stMetric"], [data-testid="stDataFrame"], .status-summary {{
    box-shadow: none !important;
    break-inside: avoid;
  }}
}}
.small-kicker {{
  display: inline-flex;
  align-items: center;
  margin-bottom: 0.45rem;
  padding: 0.28rem 0.58rem;
  color: var(--accent-cyan-text);
  background: var(--accent-cyan-soft);
  border: 1px solid rgba(6, 182, 212, 0.25);
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
</style>
"""


def apply_theme() -> None:
    """Injecte la charte centralisée dans la page Streamlit."""
    st.markdown(_STYLE, unsafe_allow_html=True)

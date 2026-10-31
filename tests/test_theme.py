from __future__ import annotations

from app.layout import status_description
from app.theme import PALETTE, _STYLE
from visualization.chart_style import (
    POINT_COLORS,
    STRATEGY_COLORS,
    apply_chart_layout,
    strategy_color,
)
import plotly.graph_objects as go


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_status_description_is_explicit_without_colour() -> None:
    assert status_description("PASS") == "PASS : les contrôles automatiques sont réussis"
    assert "WARN" in status_description("WARN")
    assert "échec" in status_description("FAIL")
    assert "non documenté" in status_description("UNKNOWN")


def test_theme_uses_the_recommended_tech_saas_palette() -> None:
    expected = {
        "bg-main": "#F8FAFC",
        "bg-surface": "#FFFFFF",
        "border-subtle": "#E2E8F0",
        "text-main": "#0F172A",
        "text-muted": "#475569",
        "sidebar-bg": "#1E293B",
        "accent-primary": "#5B52E8",
        "accent-hover": "#4F46E5",
        "accent-cyan": "#06B6D4",
    }

    assert {token: PALETTE[token] for token in expected} == expected
    assert PALETTE["accent-cyan-soft"] == "#E0F2FE"
    assert PALETTE["accent-cyan-text"] == "#0E7490"


def test_theme_applies_surfaces_navigation_and_soft_card_shadows() -> None:
    assert "background-color: var(--bg-main);" in _STYLE
    assert "background-color: var(--sidebar-bg);" in _STYLE
    assert 'a[aria-current="page"]' in _STYLE
    normalized_css = " ".join(_STYLE.split())
    assert (
        '[data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] p '
        '{ color: #CBD5E1; }'
    ) in normalized_css
    assert "background: var(--accent-cyan-soft);" in _STYLE
    assert "color: var(--accent-cyan-text);" in _STYLE
    assert 'button[kind="primary"]' in _STYLE
    assert "var(--accent-primary)" in _STYLE
    assert "0 10px 25px -5px rgba(15, 23, 42, 0.06)" in _STYLE
    assert ".status-summary" in _STYLE
    assert "focus-visible" in _STYLE
    assert "@media print" in _STYLE
    assert "prefers-reduced-motion" in _STYLE


def test_primary_accent_meets_wcag_aa_for_text_on_light_surfaces() -> None:
    assert _contrast_ratio(PALETTE["accent-primary"], PALETTE["bg-main"]) >= 4.5
    assert _contrast_ratio(PALETTE["accent-primary"], PALETTE["bg-surface"]) >= 4.5
    assert _contrast_ratio("#FFFFFF", PALETTE["accent-primary"]) >= 4.5


def test_status_styles_are_distinct_and_accessible() -> None:
    assert '.status-summary.status-pass' in _STYLE
    assert '.status-summary.status-warn' in _STYLE
    assert '.status-summary.status-fail' in _STYLE
    assert "status-pass" in _STYLE


def test_chart_tokens_keep_strategy_and_point_semantics_stable() -> None:
    assert strategy_color("baseline_zigzag") == STRATEGY_COLORS["baseline_zigzag"]
    assert strategy_color("baseline_nn") == STRATEGY_COLORS["baseline_nn"]
    assert POINT_COLORS["retained"] != POINT_COLORS["rejected"]

    figure = apply_chart_layout(go.Figure(), height=400, legend_title="Légende")
    assert figure.layout.template.layout.plot_bgcolor == "white"
    assert figure.layout.height == 400
    assert figure.layout.legend.title.text == "Légende"

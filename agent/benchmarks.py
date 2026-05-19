from __future__ import annotations

from .models import VerticalBenchmarks

_VERTICAL_DATA: dict[str, VerticalBenchmarks] = {
    "ecomm": VerticalBenchmarks(
        vertical="ecomm",
        ctr_display_pct=0.12,
        ctr_search_pct=2.5,
        win_rate_healthy_pct=30.0,
        roas_target=3.5,
        frequency_fatigue_threshold=6.0,
        description="E-commerce display and search targeting purchase-intent audiences.",
    ),
    "fintech": VerticalBenchmarks(
        vertical="fintech",
        ctr_display_pct=0.08,
        ctr_search_pct=3.0,
        win_rate_healthy_pct=25.0,
        roas_target=2.5,
        frequency_fatigue_threshold=5.0,
        description="Financial services with strict compliance constraints and cautious audiences.",
    ),
    "gaming": VerticalBenchmarks(
        vertical="gaming",
        ctr_display_pct=0.20,
        ctr_search_pct=1.8,
        win_rate_healthy_pct=35.0,
        roas_target=2.0,
        frequency_fatigue_threshold=10.0,
        description="Mobile and PC gaming with high engagement and repeat-exposure tolerance.",
    ),
    "travel": VerticalBenchmarks(
        vertical="travel",
        ctr_display_pct=0.15,
        ctr_search_pct=2.8,
        win_rate_healthy_pct=28.0,
        roas_target=4.0,
        frequency_fatigue_threshold=5.0,
        description="Travel and hospitality with strong seasonality and high-value conversions.",
    ),
    "healthcare": VerticalBenchmarks(
        vertical="healthcare",
        ctr_display_pct=0.07,
        ctr_search_pct=3.5,
        win_rate_healthy_pct=22.0,
        roas_target=2.0,
        frequency_fatigue_threshold=4.0,
        description="Healthcare campaigns with compliance constraints and sensitive audience targeting.",
    ),
    "general": VerticalBenchmarks(
        vertical="general",
        ctr_display_pct=0.10,
        ctr_search_pct=2.0,
        win_rate_healthy_pct=30.0,
        roas_target=2.5,
        frequency_fatigue_threshold=7.0,
        description="General benchmark defaults used when no specific vertical is selected.",
    ),
}


def get_vertical_benchmarks(vertical: str) -> VerticalBenchmarks:
    return _VERTICAL_DATA.get(vertical.lower(), _VERTICAL_DATA["general"])


def list_verticals() -> list[str]:
    return sorted(_VERTICAL_DATA.keys())

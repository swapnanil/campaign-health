from __future__ import annotations

import pytest

from agent.benchmarks import get_vertical_benchmarks, list_verticals
from agent.models import VerticalBenchmarks


class TestGetVerticalBenchmarks:
    def test_returns_vertical_benchmarks_type(self):
        result = get_vertical_benchmarks("ecomm")
        assert isinstance(result, VerticalBenchmarks)

    def test_ecomm_has_higher_roas_target(self):
        ecomm = get_vertical_benchmarks("ecomm")
        general = get_vertical_benchmarks("general")
        assert ecomm.roas_target > general.roas_target

    def test_gaming_has_higher_ctr_display(self):
        gaming = get_vertical_benchmarks("gaming")
        fintech = get_vertical_benchmarks("fintech")
        assert gaming.ctr_display_pct > fintech.ctr_display_pct

    def test_gaming_tolerates_higher_frequency(self):
        gaming = get_vertical_benchmarks("gaming")
        healthcare = get_vertical_benchmarks("healthcare")
        assert gaming.frequency_fatigue_threshold > healthcare.frequency_fatigue_threshold

    def test_unknown_vertical_falls_back_to_general(self):
        unknown = get_vertical_benchmarks("automotive")
        general = get_vertical_benchmarks("general")
        assert unknown.vertical == "general"
        assert unknown.ctr_display_pct == general.ctr_display_pct

    def test_case_insensitive_lookup(self):
        result = get_vertical_benchmarks("ECOMM")
        assert result.vertical == "ecomm"

    def test_all_verticals_have_positive_values(self):
        for vertical in list_verticals():
            vb = get_vertical_benchmarks(vertical)
            assert vb.ctr_display_pct > 0
            assert vb.ctr_search_pct > 0
            assert vb.win_rate_healthy_pct > 0
            assert vb.roas_target > 0
            assert vb.frequency_fatigue_threshold > 0

    def test_description_not_empty(self):
        for vertical in list_verticals():
            vb = get_vertical_benchmarks(vertical)
            assert len(vb.description) > 10


class TestListVerticals:
    def test_returns_list(self):
        result = list_verticals()
        assert isinstance(result, list)

    def test_includes_expected_verticals(self):
        result = list_verticals()
        for v in ("ecomm", "fintech", "gaming", "travel", "healthcare", "general"):
            assert v in result

    def test_is_sorted(self):
        result = list_verticals()
        assert result == sorted(result)

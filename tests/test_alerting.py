from __future__ import annotations

import pytest

from agent.alerting import DEFAULT_ALERT_RULES, evaluate_alerts
from agent.models import AlertReport, AlertRule, CampaignMetrics


def _metrics(**kwargs) -> CampaignMetrics:
    defaults = dict(campaign_id="test", spend=10000)
    defaults.update(kwargs)
    return CampaignMetrics(**defaults)


class TestEvaluateAlerts:
    def test_no_alerts_for_healthy_campaign(self):
        m = _metrics(cpa=200, roas=3.0, win_rate=35, frequency=4, budget_utilisation=90)
        result = evaluate_alerts(m)
        assert isinstance(result, AlertReport)
        assert result.total_alerts == 0
        assert result.highest_severity == "none"

    def test_cpa_critical_triggers_alert(self):
        m = _metrics(cpa=600)
        result = evaluate_alerts(m, rules=[
            AlertRule(metric="cpa", condition="gt", threshold=500, severity="critical", label="CPA Critical"),
        ])
        assert result.total_alerts == 1
        assert result.triggers[0].severity == "critical"
        assert result.triggers[0].rule_label == "CPA Critical"

    def test_roas_critical_triggers_alert(self):
        m = _metrics(roas=0.8)
        result = evaluate_alerts(m, rules=[
            AlertRule(metric="roas", condition="lt", threshold=1.0, severity="critical", label="ROAS Critical"),
        ])
        assert result.total_alerts == 1
        assert result.highest_severity == "critical"

    def test_win_rate_warning_below_20(self):
        m = _metrics(win_rate=15)
        result = evaluate_alerts(m, rules=[
            AlertRule(metric="win_rate", condition="lt", threshold=20, severity="warning", label="Win Rate Warning"),
        ])
        assert result.total_alerts == 1
        assert result.triggers[0].severity == "warning"

    def test_frequency_fatigue_triggers(self):
        m = _metrics(frequency=9)
        result = evaluate_alerts(m, rules=[
            AlertRule(metric="frequency", condition="gt", threshold=7, severity="warning", label="Frequency Fatigue"),
        ])
        assert result.total_alerts == 1

    def test_metric_missing_skips_rule(self):
        m = _metrics()  # no cpa set
        result = evaluate_alerts(m, rules=[
            AlertRule(metric="cpa", condition="gt", threshold=500, severity="critical", label="CPA Critical"),
        ])
        assert result.total_alerts == 0

    def test_highest_severity_critical_takes_precedence(self):
        m = _metrics(cpa=600, frequency=9, budget_utilisation=60)
        rules = [
            AlertRule(metric="cpa", condition="gt", threshold=500, severity="critical", label="CPA Critical"),
            AlertRule(metric="frequency", condition="gt", threshold=7, severity="warning", label="Freq"),
            AlertRule(metric="budget_utilisation", condition="lt", threshold=70, severity="warning", label="Pacing"),
        ]
        result = evaluate_alerts(m, rules=rules)
        assert result.highest_severity == "critical"
        assert result.total_alerts == 3

    def test_default_rules_used_when_none_passed(self):
        m = _metrics(roas=0.5)
        result = evaluate_alerts(m)
        assert result.total_alerts >= 1
        assert any(t.rule_label == "ROAS Critical" for t in result.triggers)

    def test_gte_condition(self):
        m = _metrics(win_rate=20)
        result = evaluate_alerts(m, rules=[
            AlertRule(metric="win_rate", condition="lte", threshold=20, severity="warning", label="Win Rate Floor"),
        ])
        assert result.total_alerts == 1

    def test_alert_summary_mentions_campaign_id(self):
        m = _metrics(campaign_id="CAMP_XYZ", cpa=600)
        result = evaluate_alerts(m, rules=[
            AlertRule(metric="cpa", condition="gt", threshold=500, severity="critical", label="CPA"),
        ])
        assert "CAMP_XYZ" in result.alert_summary

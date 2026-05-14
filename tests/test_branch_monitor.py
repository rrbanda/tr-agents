"""Tests for Branch Network Monitoring agent construction and mock tools."""

from __future__ import annotations

import json

from google.adk import Agent
from google.adk.tools.skill_toolset import SkillToolset


def _tool_names(agent: Agent) -> set[str]:
    names: set[str] = set()
    for t in agent.tools:
        if isinstance(t, SkillToolset):
            continue
        if callable(t) and hasattr(t, "__name__"):
            names.add(t.__name__)
    return names


class TestBranchMonitorAgent:
    def test_constructs(self):
        from agents.branch_monitor.agent import root_agent

        assert isinstance(root_agent, Agent)

    def test_has_single_skill_toolset(self):
        from agents.branch_monitor.agent import root_agent

        toolsets = [t for t in root_agent.tools if isinstance(t, SkillToolset)]
        assert len(toolsets) == 1

    def test_name_matches_config(self):
        from agents.branch_monitor.agent import root_agent

        assert root_agent.name == "branch_monitor"

    def test_domain_tools_registered(self):
        from agents.branch_monitor.agent import root_agent

        names = _tool_names(root_agent)
        expected = {
            "get_branch_inventory",
            "get_weather_alerts",
            "get_power_outage_status",
            "get_isp_status",
            "get_equipment_health",
            "get_historical_incidents",
            "send_alert",
            "create_preemptive_incident",
        }
        assert expected.issubset(names), f"Missing tools: {expected - names}"


class TestBranchMonitorMockTools:
    def test_get_weather_alerts_returns_valid_json(self):
        from shared.branch_monitor_tools import get_weather_alerts

        result = json.loads(get_weather_alerts("NC", "Mecklenburg"))
        assert "alert_count" in result
        assert "alerts" in result
        assert "source" in result
        assert isinstance(result["alerts"], list)

    def test_get_weather_alerts_different_county(self):
        from shared.branch_monitor_tools import get_weather_alerts

        result = json.loads(get_weather_alerts("GA", "Fulton"))
        assert "alert_count" in result
        assert isinstance(result["alerts"], list)

    def test_get_power_outage_returns_valid_json(self):
        from shared.branch_monitor_tools import get_power_outage_status

        result = json.loads(get_power_outage_status("28202"))
        assert "zip" in result
        assert "status" in result or "source" in result

    def test_get_power_outage_different_zip(self):
        from shared.branch_monitor_tools import get_power_outage_status

        result = json.loads(get_power_outage_status("30308"))
        assert "zip" in result

    def test_get_isp_status_degraded(self):
        from shared.branch_monitor_tools import get_isp_status

        result = json.loads(get_isp_status("AT&T Business", "Charlotte"))
        assert result["status"] == "degraded"
        assert result["packet_loss_pct"] > 0

    def test_get_isp_status_normal(self):
        from shared.branch_monitor_tools import get_isp_status

        result = json.loads(get_isp_status("Comcast Business", "Atlanta"))
        assert result["status"] == "normal"

    def test_get_equipment_health_degraded(self):
        from shared.branch_monitor_tools import get_equipment_health

        result = json.loads(get_equipment_health("BR-4471"))
        assert result["primary_link"]["status"] == "degraded"
        assert result["backup_link"]["status"] == "standby"

    def test_get_equipment_health_no_backup(self):
        from shared.branch_monitor_tools import get_equipment_health

        result = json.loads(get_equipment_health("ATM-28202-A"))
        assert result["backup_link"] is None

    def test_get_branch_inventory_filtered(self):
        from shared.branch_monitor_tools import get_branch_inventory

        result = json.loads(get_branch_inventory("Charlotte"))
        assert result["total"] >= 2
        for branch in result["branches"]:
            assert branch["city"] == "Charlotte"

    def test_get_historical_incidents(self):
        from shared.branch_monitor_tools import get_historical_incidents

        result = json.loads(get_historical_incidents("BR-4471"))
        assert result["incident_count"] >= 1

    def test_send_alert(self):
        from shared.branch_monitor_tools import send_alert

        result = json.loads(send_alert("charlotte-netops", "high", "Test alert"))
        assert result["status"] == "sent"

    def test_create_preemptive_incident(self):
        from shared.branch_monitor_tools import create_preemptive_incident

        result = json.loads(create_preemptive_incident("BR-4471", "high", "Storm threat"))
        assert result["status"] == "created"
        assert "INC-" in result["incident_id"]

    def test_data_consistency(self):
        """Branch inventory ISPs match ISP status tool data."""
        from shared.branch_monitor_tools import get_branch_inventory, get_isp_status

        branches = json.loads(get_branch_inventory("Charlotte"))
        for branch in branches["branches"]:
            isp = branch["isp_primary"]
            status = json.loads(get_isp_status(isp, "Charlotte"))
            assert status.get("provider") == isp or status.get("status") == "no_data"


class TestCorrelateThreatsScript:
    def test_high_threat_scenario(self):
        """Charlotte scenario should produce HIGH/CRITICAL for BR-4471."""
        import subprocess

        input_data = {
            "branches": {
                "BR-4471": {
                    "weather": [{"severity": "severe"}],
                    "power": {"status": "active_outage", "customers_affected": 3200, "customers_total": 18500},
                    "isp": {"status": "degraded", "packet_loss_pct": 4.2},
                    "equipment": {
                        "primary_link": {"status": "degraded"},
                        "backup_link": {"status": "standby"},
                        "ups_battery_pct": 85,
                        "router": {"cpu_pct": 34, "temperature_c": 42},
                    },
                },
                "BR-5512": {
                    "weather": [],
                    "power": {"status": "normal", "customers_affected": 0, "customers_total": 22100},
                    "isp": {"status": "normal", "packet_loss_pct": 0},
                    "equipment": {
                        "primary_link": {"status": "healthy"},
                        "backup_link": {"status": "standby"},
                        "ups_battery_pct": 98,
                        "router": {"cpu_pct": 28, "temperature_c": 40},
                    },
                },
            }
        }

        proc = subprocess.run(
            ["python3", "agents/branch_monitor/skills/branch-network-monitor/scripts/correlate_threats.py"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0, f"Script failed: {proc.stderr}"
        result = json.loads(proc.stdout)
        assessments = {a["branch_id"]: a for a in result["assessments"]}

        assert assessments["BR-4471"]["threat_level"] in ("HIGH", "CRITICAL")
        assert assessments["BR-4471"]["threat_score"] >= 60
        assert assessments["BR-5512"]["threat_level"] == "LOW"
        assert assessments["BR-5512"]["threat_score"] < 40

"""Tests for F5 VIP Provisioning agent construction and mock tools."""

from __future__ import annotations

import json
import subprocess

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


class TestF5ProvisioningAgent:
    def test_constructs(self):
        from agents.f5_provisioning.agent import root_agent

        assert isinstance(root_agent, Agent)

    def test_has_single_skill_toolset(self):
        from agents.f5_provisioning.agent import root_agent

        toolsets = [t for t in root_agent.tools if isinstance(t, SkillToolset)]
        assert len(toolsets) == 1

    def test_name_matches_config(self):
        from agents.f5_provisioning.agent import root_agent

        assert root_agent.name == "f5_provisioning"

    def test_domain_tools_registered(self):
        from agents.f5_provisioning.agent import root_agent

        names = _tool_names(root_agent)
        expected = {
            "get_servicenow_request",
            "get_dns_assignment",
            "get_naming_conventions",
            "get_subnet_info",
            "get_historical_assignments",
            "get_f5_config",
            "run_connectivity_check",
            "submit_evidence_package",
        }
        assert expected.issubset(names), f"Missing tools: {expected - names}"


class TestF5MockTools:
    def test_get_request(self):
        from shared.f5_tools import get_servicenow_request

        result = json.loads(get_servicenow_request("REQ-2025-0847"))
        assert result["environment"] == "production"
        assert result["vip_name"] == "vs-onlinebanking-prod-443"

    def test_get_dns_assignment(self):
        from shared.f5_tools import get_dns_assignment

        result = json.loads(get_dns_assignment("REQ-2025-0847"))
        assert result["assigned_ip"] == "10.120.100.25"
        assert "prod" in result["hostname"]

    def test_get_naming_conventions(self):
        from shared.f5_tools import get_naming_conventions

        result = json.loads(get_naming_conventions("production"))
        assert result["subnet_prefix"] == "10.120."

    def test_get_subnet_info(self):
        from shared.f5_tools import get_subnet_info

        result = json.loads(get_subnet_info("10.120.100.25"))
        assert result["environment"] == "production"

    def test_run_connectivity_check(self):
        from shared.f5_tools import run_connectivity_check

        result = json.loads(run_connectivity_check("10.120.100.25", "10.120.50.11:8443,10.120.50.12:8443"))
        assert result["all_healthy"] is True

    def test_submit_evidence(self):
        from shared.f5_tools import submit_evidence_package

        result = json.loads(submit_evidence_package("REQ-2025-0847", '{"test": true}'))
        assert result["status"] == "evidence_submitted"


class TestValidationScript:
    def test_valid_production_assignment(self):
        input_data = {
            "hostname": "onlinebanking.prod.internal.bank.com",
            "ip": "10.120.100.25",
            "environment": "production",
            "subnet": "10.120.100.0/24",
            "vlan": "VLAN-120",
            "conventions": {
                "hostname_pattern": "{app}.prod.internal.bank.com",
                "subnet_prefix": "10.120.",
                "vlan_range": ["VLAN-120", "VLAN-121", "VLAN-122"],
            },
        }
        proc = subprocess.run(
            ["python3", "agents/f5_provisioning/skills/f5-dns-validator/scripts/validate_naming.py"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["overall"] == "PASS"

    def test_staging_ip_for_production_request(self):
        """The classic DNS team error: staging IP assigned to production."""
        input_data = {
            "hostname": "mobilegw-stg.prod.internal.bank.com",
            "ip": "10.120.100.30",
            "environment": "staging",
            "subnet": "10.120.100.0/24",
            "vlan": "VLAN-120",
            "conventions": {
                "hostname_pattern": "{app}.stg.internal.bank.com",
                "subnet_prefix": "10.130.",
                "vlan_range": ["VLAN-130", "VLAN-131"],
            },
        }
        proc = subprocess.run(
            ["python3", "agents/f5_provisioning/skills/f5-dns-validator/scripts/validate_naming.py"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["overall"] == "FAIL"
        fail_rules = [f["rule"] for f in result["findings"] if f["status"] == "FAIL"]
        assert "ip_subnet_prefix" in fail_rules

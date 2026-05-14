"""F5 VIP Provisioning Agent -- DNS Validation and Evidence Synthesis.

Uses agentskills.io skills with executable scripts for deterministic
validation of DNS/IP assignments against naming conventions. Called by
the RHDH Orchestrator workflow at AI reasoning stages.
"""

import pathlib

from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset

from shared.f5_tools import (
    get_dns_assignment,
    get_f5_config,
    get_historical_assignments,
    get_naming_conventions,
    get_servicenow_request,
    get_subnet_info,
    run_connectivity_check,
    submit_evidence_package,
)
from shared.model_config import get_agent_config, get_agent_model

_cfg = get_agent_config("f5_provisioning")
_skills_dir = pathlib.Path(__file__).parent / "skills"

_validator_skill = load_skill_from_dir(_skills_dir / "f5-dns-validator")
_skill_toolset = SkillToolset(skills=[_validator_skill])

root_agent = Agent(
    model=get_agent_model(),
    name=_cfg["name"],
    description=_cfg["description"],
    instruction=(
        "You are an F5 VIP Provisioning agent that validates DNS/IP assignments "
        "and synthesizes evidence for approval workflows.\n\n"
        "You are called by the RHDH Orchestrator workflow at two stages:\n"
        "1. After DNS/IP assignment -- to validate before F5 configuration\n"
        "2. After F5 configuration -- to synthesize evidence for approval\n\n"
        "Workflow:\n"
        "1. Load the f5-dns-validator skill for your validation methodology\n"
        "2. Use get_servicenow_request to get the provisioning request details\n"
        "3. Use get_dns_assignment to get the assigned IPs and hostnames\n"
        "4. Use get_naming_conventions for the target environment's rules\n"
        "5. Use run_skill_script to execute scripts/validate_naming.py for "
        "deterministic validation (do NOT try to validate naming rules yourself)\n"
        "6. Use get_subnet_info to verify subnet environment and purpose\n"
        "7. Use get_historical_assignments to check for similar past patterns\n"
        "8. If asked to review a completed configuration, use get_f5_config "
        "and run_connectivity_check to verify the VIP is working\n"
        "9. Present validation results with clear pass/fail per rule\n"
        "10. If all checks pass, use submit_evidence_package to send the "
        "evidence to ServiceNow for F5 team approval\n\n"
        "Rules:\n"
        "- Always use the validation script for naming checks -- never guess\n"
        "- If validation fails, explain exactly what's wrong and what the "
        "correct values should be based on the naming conventions\n"
        "- Reference historical assignments when a similar error has occurred\n"
        "- Be specific: cite the rule, the expected value, and the actual value\n"
        "- The F5 network team will review your evidence -- be thorough"
    ),
    tools=[
        _skill_toolset,
        get_servicenow_request,
        get_dns_assignment,
        get_naming_conventions,
        get_subnet_info,
        get_historical_assignments,
        get_f5_config,
        run_connectivity_check,
        submit_evidence_package,
    ],
)

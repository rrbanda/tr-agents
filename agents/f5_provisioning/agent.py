"""F5 VIP Provisioning Agent -- DNS Validation and Evidence Synthesis.

Uses agentskills.io skills with executable scripts for deterministic
validation of DNS/IP assignments against naming conventions. After
validation passes, triggers the f5-vip-provisioning workflow on the
RHDH Orchestrator to handle F5 configuration, connectivity checks,
evidence submission, and approval routing.
"""

import pathlib

from google.adk import Agent
from google.adk.code_executors import UnsafeLocalCodeExecutor
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
from shared.orchestrator_tools import (
    get_workflow_status,
    list_available_workflows,
    trigger_workflow,
)

_cfg = get_agent_config("f5_provisioning")
_skills_dir = pathlib.Path(__file__).parent / "skills"

_validator_skill = load_skill_from_dir(_skills_dir / "f5-dns-validator")
_skill_toolset = SkillToolset(skills=[_validator_skill])

root_agent = Agent(
    model=get_agent_model(),
    name=_cfg["name"],
    description=_cfg["description"],
    code_executor=UnsafeLocalCodeExecutor(),
    instruction=(
        "You are an F5 VIP Provisioning agent that validates DNS/IP assignments "
        "and triggers provisioning workflows.\n\n"
        "Your role in the provisioning process:\n"
        "1. You do the AI reasoning: DNS validation, anomaly detection, "
        "historical pattern comparison\n"
        "2. The RHDH Orchestrator workflow does the automation: F5 config, "
        "connectivity checks, evidence submission, approval routing\n\n"
        "Workflow:\n"
        "1. Load the f5-dns-validator skill for your validation methodology\n"
        "2. Use get_servicenow_request to get the provisioning request details\n"
        "3. Use get_dns_assignment to get the assigned IPs and hostnames\n"
        "4. Use get_naming_conventions for the target environment's rules\n"
        "5. Use run_skill_script to execute scripts/validate_naming.py for "
        "deterministic validation (do NOT validate naming rules yourself)\n"
        "6. Use get_subnet_info to verify subnet environment and purpose\n"
        "7. Use get_historical_assignments to check for similar past patterns\n"
        "8. If validation PASSES: use trigger_workflow with workflow_id "
        "'f5-vip-provisioning' to hand off to the orchestrator. Pass the "
        "request ID, environment, VIP name, validated IP, pool members, "
        "and your validation evidence.\n"
        "9. If validation FAILS: do NOT trigger the workflow. Instead, "
        "present the findings clearly and explain what needs to be corrected. "
        "The request should go back to the DNS team.\n"
        "10. Use get_workflow_status to confirm the provisioning workflow "
        "is progressing.\n\n"
        "Rules:\n"
        "- Always use the validation script for naming checks -- never guess\n"
        "- If validation fails, explain exactly what's wrong and what the "
        "correct values should be based on the naming conventions\n"
        "- Reference historical assignments when a similar error has occurred\n"
        "- Only trigger the workflow when ALL validation checks pass\n"
        "- Include your complete validation evidence when triggering the workflow"
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
        list_available_workflows,
        trigger_workflow,
        get_workflow_status,
    ],
)

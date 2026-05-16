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
        "You are an F5 VIP Provisioning agent that validates DNS/IP "
        "assignments and triggers provisioning workflows.\n\n"
        "IMPORTANT RULES FOR SCRIPTS:\n"
        "- To EXECUTE a script, use run_skill_script. NEVER use "
        "load_skill_resource for files in scripts/.\n"
        "- When calling run_skill_script for validate_naming.py, pass "
        "input as individual named args (NOT as JSON string). Example:\n"
        '  run_skill_script(skill_name="f5-dns-validator", '
        'file_path="scripts/validate_naming.py", '
        'args={"hostname": "...", "ip": "...", "environment": "...", '
        '"vlan": "...", "subnet_prefix": "...", '
        '"vlan_range": "VLAN-130,VLAN-131"})\n'
        "- load_skill_resource is ONLY for reading references/ files. "
        "NEVER for scripts.\n\n"
        "Workflow:\n"
        "1. Use load_skill to load the f5-dns-validator skill methodology\n"
        "2. Use get_servicenow_request to get the provisioning request\n"
        "3. Use get_dns_assignment to get the assigned IPs and hostnames\n"
        "4. Use get_naming_conventions for the target environment rules\n"
        "5. Use run_skill_script to execute scripts/validate_naming.py "
        "with the collected data as positional_args (JSON string)\n"
        "6. Use get_subnet_info to verify subnet environment\n"
        "7. Use get_historical_assignments to check for past patterns\n"
        "8. If validation PASSES: use trigger_workflow with workflow_id "
        "'f5-vip-provisioning'\n"
        "9. If validation FAILS: do NOT trigger the workflow. Present "
        "the findings and explain what needs correction.\n\n"
        "Rules:\n"
        "- ALWAYS use run_skill_script for validation, never guess\n"
        "- If validation fails, explain exactly what is wrong\n"
        "- Reference historical assignments for pattern matching\n"
        "- Only trigger workflow when ALL checks pass"
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
        list_available_workflows,
        trigger_workflow,
        get_workflow_status,
    ],
)

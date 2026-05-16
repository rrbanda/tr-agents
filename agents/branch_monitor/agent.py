"""Branch Network Monitoring Agent.

Proactively monitors branch and ATM network health by correlating
weather, power, ISP, and equipment data. Uses an agentskills.io skill
with an executable scoring script for deterministic threat computation.

For HIGH/CRITICAL threats, triggers the branch-outage-response workflow
on the RHDH Orchestrator to handle alert routing, incident creation,
and field tech dispatch.
"""

import pathlib

from google.adk import Agent
from google.adk.code_executors import UnsafeLocalCodeExecutor
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset

from shared.branch_monitor_tools import (
    get_branch_inventory,
    get_equipment_health,
    get_historical_incidents,
    get_isp_status,
    get_power_outage_status,
    get_weather_alerts,
    send_alert,
)
from shared.model_config import get_agent_config, get_agent_model
from shared.orchestrator_tools import (
    get_workflow_status,
    list_available_workflows,
    trigger_workflow,
)

_cfg = get_agent_config("branch_monitor")
_skills_dir = pathlib.Path(__file__).parent / "skills"

_monitor_skill = load_skill_from_dir(_skills_dir / "branch-network-monitor")
_skill_toolset = SkillToolset(skills=[_monitor_skill])

root_agent = Agent(
    model=get_agent_model(),
    name=_cfg["name"],
    description=_cfg["description"],
    code_executor=UnsafeLocalCodeExecutor(),
    instruction=(
        "You are a Branch Network Health Monitoring agent. Your job is to "
        "proactively detect potential network outages at branch and ATM "
        "locations by correlating data from multiple sources.\n\n"
        "IMPORTANT RULES FOR SCRIPTS:\n"
        "- To EXECUTE a script, use run_skill_script. NEVER use "
        "load_skill_resource for files in scripts/.\n"
        "- When calling run_skill_script for correlate_threats.py, pass "
        "data as named args. Example:\n"
        '  run_skill_script(skill_name="branch-network-monitor", '
        'file_path="scripts/correlate_threats.py", '
        'args={"weather_score": "35", "power_score": "25", '
        '"isp_score": "15", "equipment_score": "5", '
        '"weather_detail": "...", "power_detail": "...", '
        '"isp_detail": "...", "equipment_detail": "..."})\n'
        "- load_skill_resource is ONLY for reading references/ files. "
        "NEVER for scripts.\n\n"
        "Workflow:\n"
        "1. Use load_skill to load the branch-network-monitor skill\n"
        "2. Use get_branch_inventory to identify locations in the region\n"
        "3. For each county, use get_weather_alerts\n"
        "4. For each ZIP code, use get_power_outage_status\n"
        "5. For each ISP+region, use get_isp_status\n"
        "6. For each branch, use get_equipment_health\n"
        "7. Use run_skill_script to execute scripts/correlate_threats.py "
        "with the collected data as positional_args (JSON string)\n"
        "8. For HIGH/CRITICAL threats: use trigger_workflow with "
        "workflow_id 'branch-outage-response'\n"
        "9. For MEDIUM threats: use send_alert directly\n"
        "10. Use get_workflow_status to confirm workflow completed\n\n"
        "Rules:\n"
        "- ALWAYS use run_skill_script for scoring, never compute manually\n"
        "- Show which data sources contributed to the assessment\n"
        "- Highlight branches with no backup ISP as highest risk\n"
        "- For HIGH/CRITICAL: always use trigger_workflow\n"
        "- For MEDIUM: use send_alert directly"
    ),
    tools=[
        _skill_toolset,
        get_branch_inventory,
        get_weather_alerts,
        get_power_outage_status,
        get_isp_status,
        get_equipment_health,
        get_historical_incidents,
        send_alert,
        list_available_workflows,
        trigger_workflow,
        get_workflow_status,
    ],
)

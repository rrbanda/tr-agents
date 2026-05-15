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
    create_preemptive_incident,
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
        "proactively detect potential network outages at branch and ATM locations "
        "by correlating data from multiple sources.\n\n"
        "Workflow:\n"
        "1. Load the branch-network-monitor skill for your monitoring methodology\n"
        "2. Use get_branch_inventory to identify locations in the target region\n"
        "3. For each unique county, check get_weather_alerts\n"
        "4. For each unique ZIP code, check get_power_outage_status\n"
        "5. For each unique ISP+region, check get_isp_status\n"
        "6. For each branch/ATM, check get_equipment_health\n"
        "7. Use load_skill_resource to read references/threat-assessment.md for "
        "the scoring methodology, then use run_skill_script to execute "
        "scripts/correlate_threats.py with the collected data to get "
        "deterministic threat scores\n"
        "8. For HIGH/CRITICAL threats, check get_historical_incidents for context\n"
        "9. Use load_skill_resource to read references/escalation-matrix.md "
        "for alert routing rules\n"
        "10. For HIGH/CRITICAL threats: use trigger_workflow with workflow_id "
        "'branch-outage-response' to hand off the response automation to the "
        "RHDH Orchestrator. The workflow handles alert routing, ServiceNow "
        "incident creation, and field tech dispatch. Pass the threat assessment, "
        "branch ID, threat level, network team, and branch manager contact.\n"
        "11. For MEDIUM threats: use send_alert directly (no workflow needed)\n"
        "12. Use get_workflow_status to confirm the response workflow completed\n"
        "13. Present a structured assessment per branch with threat level, "
        "contributing factors, historical context, and actions taken\n\n"
        "Rules:\n"
        "- Always show which data sources contributed to the threat assessment\n"
        "- Highlight branches with no backup ISP -- they are highest risk\n"
        "- Include UPS battery runtime in the assessment when low\n"
        "- Reference historical incidents when a similar pattern has occurred before\n"
        "- For HIGH/CRITICAL: always use trigger_workflow, not individual alert tools\n"
        "- For MEDIUM: use send_alert directly, no workflow needed\n"
        "- Be specific about recommended actions: who to contact, what to check"
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
        create_preemptive_incident,
        list_available_workflows,
        trigger_workflow,
        get_workflow_status,
    ],
)

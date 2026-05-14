"""A2A server entrypoint for the Branch Network Monitoring agent."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

import litellm  # noqa: E402

litellm.disable_aiohttp_transport = True

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from a2a.types import AgentCapabilities, AgentCard, AgentSkill  # noqa: E402
from google.adk.a2a.utils.agent_to_a2a import to_a2a  # noqa: E402

from shared.model_config import get_agent_config  # noqa: E402

from .agent import root_agent  # noqa: E402

_cfg = get_agent_config("branch_monitor")
_a2a_cfg = _cfg.get("a2a", {})
_host = _cfg.get("host", "0.0.0.0")
_port = int(_cfg.get("port", 8001))

_agent_card = AgentCard(
    name="Branch Network Monitor",
    description=_cfg["description"],
    url=f"http://{_host}:{_port}/",
    version=_a2a_cfg.get("version", "0.1.0"),
    default_input_modes=["text/plain"],
    default_output_modes=["application/json"],
    capabilities=AgentCapabilities(streaming=False, push_notifications=False),
    skills=[
        AgentSkill(
            id="threat-assessment",
            name="Network Threat Assessment",
            description=(
                "Correlates weather, power, ISP, and equipment data to assess "
                "threat levels per branch/ATM location."
            ),
            tags=["monitoring", "proactive", "correlation", "network"],
        ),
        AgentSkill(
            id="proactive-alerting",
            name="Proactive Alerting",
            description=(
                "Sends alerts to network teams and branch managers, creates "
                "preemptive ServiceNow incidents for HIGH/CRITICAL threats."
            ),
            tags=["alerting", "servicenow", "escalation"],
        ),
    ],
)

app = to_a2a(
    root_agent,
    host=_host,
    port=_port,
    protocol="http",
    agent_card=_agent_card,
)

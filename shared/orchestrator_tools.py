"""RHDH Orchestrator integration tools.

Provides tools for agents to trigger and monitor SonataFlow workflows
running on the RHDH Orchestrator. The agent decides WHEN to trigger
a workflow based on its AI reasoning; the workflow handles the
deterministic automation steps.

In production, these call the RHDH Orchestrator REST API.
Currently returns mock responses for POC demonstration.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_ORCHESTRATOR_URL = "http://sonataflow-platform.orchestrator.svc.cluster.local"

_MOCK_WORKFLOWS: dict[str, dict[str, Any]] = {
    "f5-vip-provisioning": {
        "id": "f5-vip-provisioning",
        "name": "F5 VIP Provisioning",
        "description": (
            "Provisions F5 VIP after DNS validation passes. Configures F5, "
            "runs connectivity checks, submits evidence for approval."
        ),
        "version": "1.0",
        "input_schema": {
            "required": ["requestId", "environment", "vipName", "assignedIp", "poolMembers"],
            "properties": {
                "requestId": "ServiceNow request ID",
                "environment": "production | staging | development",
                "vipName": "VIP name for F5",
                "assignedIp": "Validated IP from Infoblox",
                "poolMembers": "Comma-separated pool member addresses",
                "validationEvidence": "Agent's DNS validation findings",
            },
        },
    },
    "branch-outage-response": {
        "id": "branch-outage-response",
        "name": "Branch Outage Response",
        "description": (
            "Executes response actions for branch network threats. Sends alerts, "
            "creates ServiceNow incidents, and dispatches field techs."
        ),
        "version": "1.0",
        "input_schema": {
            "required": ["branchId", "threatLevel", "assessmentSummary"],
            "properties": {
                "branchId": "Branch or ATM identifier",
                "threatLevel": "CRITICAL | HIGH | MEDIUM",
                "threatScore": "Numeric score 0-100",
                "assessmentSummary": "Agent's threat assessment text",
                "contributingFactors": "JSON array of factors",
                "networkTeam": "Regional network ops team name",
                "branchManagerPhone": "Branch manager contact",
                "recommendedActions": "JSON array of recommended actions",
            },
        },
    },
}


def list_available_workflows() -> str:
    """List available RHDH Orchestrator workflows that can be triggered.

    Returns:
        JSON string with workflow IDs, names, descriptions, and input schemas.
    """
    workflows = [
        {
            "id": w["id"],
            "name": w["name"],
            "description": w["description"],
            "version": w["version"],
            "input_schema": w["input_schema"],
        }
        for w in _MOCK_WORKFLOWS.values()
    ]
    return json.dumps({"workflows": workflows}, indent=2)


def trigger_workflow(workflow_id: str, input_data: str) -> str:
    """Trigger an RHDH Orchestrator workflow to execute deterministic automation.

    The agent calls this after completing AI reasoning (e.g., DNS validation
    passed, threat assessment computed) to hand off to the workflow engine
    for the automation steps (F5 config, alerts, ticket creation, etc.).

    In production, this POSTs to the RHDH Orchestrator REST API:
    POST /v2/workflows/{workflow_id}/instances

    Args:
        workflow_id: Workflow to trigger (e.g. 'f5-vip-provisioning',
            'branch-outage-response'). Use list_available_workflows to see options.
        input_data: JSON string matching the workflow's input schema.

    Returns:
        JSON string with the workflow instance ID and status.
    """
    wf = _MOCK_WORKFLOWS.get(workflow_id)
    if wf is None:
        return json.dumps({
            "error": f"Workflow '{workflow_id}' not found. Use list_available_workflows to see options."
        })

    try:
        parsed_input = json.loads(input_data)
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"error": f"Invalid JSON input: {e}"})

    required = wf["input_schema"].get("required", [])
    missing = [f for f in required if f not in parsed_input]
    if missing:
        return json.dumps({"error": f"Missing required fields: {missing}", "schema": wf["input_schema"]})

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    instance_id = f"wf-{workflow_id[:10]}-{now[:10].replace('-', '')}"

    logger.info(
        "Workflow triggered: %s (instance: %s) with %d input fields",
        workflow_id,
        instance_id,
        len(parsed_input),
    )

    return json.dumps(
        {
            "status": "triggered",
            "workflow_id": workflow_id,
            "workflow_name": wf["name"],
            "instance_id": instance_id,
            "triggered_at": now,
            "input_accepted": True,
            "message": (
                f"Workflow '{wf['name']}' started. "
                f"The orchestrator will handle the automation steps. "
                f"Track progress in RHDH Backstage UI or call get_workflow_status."
            ),
        },
        indent=2,
    )


def get_workflow_status(instance_id: str) -> str:
    """Check the status of a triggered workflow instance.

    In production, this calls GET /v2/workflows/instances/{instance_id}
    on the RHDH Orchestrator REST API.

    Args:
        instance_id: Workflow instance ID returned by trigger_workflow.

    Returns:
        JSON string with workflow status, completed steps, and any outputs.
    """
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if "f5-vip" in instance_id:
        return json.dumps(
            {
                "instance_id": instance_id,
                "workflow_id": "f5-vip-provisioning",
                "status": "completed",
                "started_at": now,
                "completed_at": now,
                "steps_completed": [
                    {"step": "Configure F5 VIP", "status": "done", "duration_ms": 3200},
                    {"step": "Run connectivity checks", "status": "done", "duration_ms": 1500},
                    {"step": "Submit evidence to ServiceNow", "status": "done", "duration_ms": 800},
                    {"step": "Request F5 team approval", "status": "pending_approval"},
                ],
                "message": "VIP configured and evidence submitted. Awaiting F5 team approval in RHDH Backstage.",
            },
            indent=2,
        )

    if "branch-out" in instance_id:
        return json.dumps(
            {
                "instance_id": instance_id,
                "workflow_id": "branch-outage-response",
                "status": "completed",
                "started_at": now,
                "completed_at": now,
                "steps_completed": [
                    {"step": "Send Teams alert to network team", "status": "done", "duration_ms": 500},
                    {"step": "Send SMS to branch manager", "status": "done", "duration_ms": 1200},
                    {"step": "Create ServiceNow incident", "status": "done", "incident_id": "INC-2025-05-14-001"},
                    {"step": "Check field tech availability", "status": "done"},
                    {"step": "Schedule field tech dispatch", "status": "done"},
                ],
                "message": "All response actions completed. Incident created, team alerted, tech dispatched.",
            },
            indent=2,
        )

    return json.dumps({"instance_id": instance_id, "status": "not_found"})

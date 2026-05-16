"""RHDH Orchestrator integration tools.

Provides tools for agents to trigger and monitor SonataFlow workflows
running on the RHDH Orchestrator. The agent decides WHEN to trigger
a workflow based on its AI reasoning; the workflow handles the
deterministic automation steps.

Calls the SonataFlow REST API (Quarkus process management) and
the Data-Index GraphQL service for workflow status queries.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SONATAFLOW_NS = os.environ.get("SONATAFLOW_NAMESPACE", "sonataflow-infra")
_DATA_INDEX_URL = os.environ.get(
    "DATA_INDEX_URL",
    f"http://sonataflow-platform-data-index-service.{_SONATAFLOW_NS}.svc.cluster.local",
)

_WORKFLOW_REGISTRY: dict[str, dict[str, Any]] = {
    "f5-vip-provisioning": {
        "id": "f5-vip-provisioning",
        "name": "F5 VIP Provisioning",
        "description": (
            "Provisions F5 VIP after DNS validation passes. Configures F5, "
            "runs connectivity checks, submits evidence for approval."
        ),
        "version": "1.0",
        "service_url": f"http://f5-vip-provisioning.{_SONATAFLOW_NS}.svc.cluster.local:8080",
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
        "service_url": f"http://branch-outage-response.{_SONATAFLOW_NS}.svc.cluster.local:8080",
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

_HTTP_TIMEOUT = 10.0


def list_available_workflows() -> str:
    """List available RHDH Orchestrator workflows that can be triggered.

    Queries the Data-Index GraphQL service for running workflow definitions.
    Falls back to the local registry if the service is unreachable.

    Returns:
        JSON string with workflow IDs, names, descriptions, and input schemas.
    """
    for wf_id, wf in _WORKFLOW_REGISTRY.items():
        try:
            resp = httpx.get(
                f"{wf['service_url']}/management/processes",
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code == 200:
                definitions = resp.json()
                for defn in definitions:
                    reg = _WORKFLOW_REGISTRY.get(defn["id"])
                    if reg:
                        defn["input_schema"] = reg["input_schema"]
                return json.dumps({"workflows": definitions, "source": "workflow-executor"}, indent=2)
        except Exception as e:
            logger.warning("Workflow executor query failed for %s: %s", wf_id, e)
            break

    workflows = [
        {
            "id": w["id"],
            "name": w["name"],
            "description": w["description"],
            "version": w["version"],
            "input_schema": w["input_schema"],
        }
        for w in _WORKFLOW_REGISTRY.values()
    ]
    return json.dumps({"workflows": workflows, "source": "local-registry"}, indent=2)


def trigger_workflow(workflow_id: str, input_data: str) -> str:
    """Trigger an RHDH Orchestrator workflow to execute deterministic automation.

    The agent calls this after completing AI reasoning (e.g., DNS validation
    passed, threat assessment computed) to hand off to the workflow engine
    for the automation steps (F5 config, alerts, ticket creation, etc.).

    Sends a POST to the SonataFlow process management API:
    POST /{workflow_id}

    Args:
        workflow_id: Workflow to trigger (e.g. 'f5-vip-provisioning',
            'branch-outage-response'). Use list_available_workflows to see options.
        input_data: JSON string matching the workflow's input schema.

    Returns:
        JSON string with the workflow instance ID and status.
    """
    wf = _WORKFLOW_REGISTRY.get(workflow_id)
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

    service_url = wf["service_url"]
    endpoint = f"{service_url}/{workflow_id}"

    try:
        resp = httpx.post(
            endpoint,
            json=parsed_input,
            headers={"Content-Type": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )

        logger.info(
            "Workflow %s trigger response: status=%d",
            workflow_id,
            resp.status_code,
        )

        if resp.status_code in (200, 201):
            result = resp.json()
            instance_id = result.get("id", "unknown")
            return json.dumps(
                {
                    "status": "triggered",
                    "workflow_id": workflow_id,
                    "workflow_name": wf["name"],
                    "instance_id": instance_id,
                    "response": result,
                    "message": (
                        f"Workflow '{wf['name']}' started (instance: {instance_id}). "
                        f"The orchestrator is executing the automation steps. "
                        f"Use get_workflow_status to check progress."
                    ),
                },
                indent=2,
            )
        else:
            return json.dumps({
                "error": f"Workflow trigger failed: HTTP {resp.status_code}",
                "detail": resp.text[:500],
                "endpoint": endpoint,
            })

    except httpx.TimeoutException:
        return json.dumps({"error": f"Timeout calling {endpoint}", "workflow_id": workflow_id})
    except httpx.ConnectError as e:
        return json.dumps({
            "error": f"Cannot connect to workflow service: {e}",
            "endpoint": endpoint,
            "hint": "Ensure the SonataFlow workflow is deployed and running in the cluster.",
        })
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {e}", "workflow_id": workflow_id})


def get_workflow_status(instance_id: str) -> str:
    """Check the status of a triggered workflow instance.

    Queries the SonataFlow Data-Index GraphQL service for instance details
    including state, nodes executed, variables, and any errors.

    Args:
        instance_id: Workflow instance ID returned by trigger_workflow.

    Returns:
        JSON string with workflow status, nodes executed, and any outputs.
    """
    query = json.dumps({
        "query": """
            query($id: String!) {
                ProcessInstances(where: {id: {equal: $id}}) {
                    id
                    processId
                    processName
                    state
                    start
                    end
                    variables
                    nodes {
                        name
                        type
                        enter
                        exit
                    }
                    error {
                        message
                        nodeDefinitionId
                    }
                }
            }
        """,
        "variables": {"id": instance_id},
    })

    try:
        resp = httpx.post(
            f"{_DATA_INDEX_URL}/graphql",
            content=query,
            headers={"Content-Type": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )

        if resp.status_code == 200:
            data = resp.json()
            instances = data.get("data", {}).get("ProcessInstances", [])
            if instances:
                inst = instances[0]
                nodes_completed = [
                    {"name": n["name"], "type": n["type"], "entered": n.get("enter"), "exited": n.get("exit")}
                    for n in inst.get("nodes", [])
                    if n.get("exit")
                ]
                result = {
                    "instance_id": inst["id"],
                    "workflow_id": inst.get("processId"),
                    "workflow_name": inst.get("processName"),
                    "status": _map_state(inst.get("state", "UNKNOWN")),
                    "started_at": inst.get("start"),
                    "completed_at": inst.get("end"),
                    "nodes_completed": nodes_completed,
                    "source": "data-index",
                }
                if inst.get("error"):
                    result["error"] = inst["error"]
                if inst.get("variables"):
                    variables = inst["variables"]
                    if isinstance(variables, str):
                        try:
                            variables = json.loads(variables)
                        except (json.JSONDecodeError, TypeError):
                            variables = {}
                    wfdata = variables.get("workflowdata", variables)
                    if "result" in wfdata:
                        result["output"] = wfdata["result"]
                return json.dumps(result, indent=2)
            else:
                return json.dumps({"instance_id": instance_id, "status": "not_found"})
        else:
            return json.dumps({
                "error": f"Data-Index query failed: HTTP {resp.status_code}",
                "detail": resp.text[:500],
            })

    except Exception as e:
        return json.dumps({"error": f"Failed to query workflow status: {e}", "instance_id": instance_id})


def _map_state(state: str) -> str:
    """Map SonataFlow internal state codes to human-readable status."""
    mapping = {
        "ACTIVE": "running",
        "COMPLETED": "completed",
        "ERROR": "error",
        "ABORTED": "aborted",
        "SUSPENDED": "suspended",
        "PENDING": "pending",
    }
    return mapping.get(state, state.lower())

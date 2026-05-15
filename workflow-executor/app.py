"""SonataFlow-compatible workflow executor.

Implements the Kogito/SonataFlow process management REST API and executes
the branch-outage-response and f5-vip-provisioning workflow logic by calling
the mock backend services.

REST API surface:
  GET  /management/processes                           - list process definitions
  POST /{processId}                                    - start a new instance
  GET  /management/processes/{processId}/instances/{id} - get instance status
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflow-executor")

MOCK_BACKEND = os.environ.get("MOCK_BACKEND_URL", "http://mock-workflow-backends:8080")
app = FastAPI(title="SonataFlow Workflow Executor")

_instances: dict[str, dict[str, Any]] = {}

PROCESS_DEFINITIONS = {
    "branch-outage-response": {
        "id": "branch-outage-response",
        "name": "Branch Outage Response",
        "version": "1.0",
        "description": "Triggered by the Branch Monitor agent for HIGH/CRITICAL threats. "
                        "Sends alerts, creates ServiceNow incidents, dispatches field techs.",
    },
    "f5-vip-provisioning": {
        "id": "f5-vip-provisioning",
        "name": "F5 VIP Provisioning",
        "version": "1.0",
        "description": "Provisions F5 VIP after DNS validation passes. "
                        "Configures F5, runs connectivity checks, submits evidence.",
    },
}


@app.get("/management/processes")
async def list_processes():
    return list(PROCESS_DEFINITIONS.values())


@app.post("/branch-outage-response")
async def start_branch_outage(request: Request):
    """Execute the branch-outage-response workflow."""
    data = await request.json()
    instance_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    instance = {
        "id": instance_id,
        "processId": "branch-outage-response",
        "processName": "Branch Outage Response",
        "state": "ACTIVE",
        "start": now,
        "end": None,
        "variables": data,
        "nodes": [],
        "error": None,
    }
    _instances[instance_id] = instance

    asyncio.create_task(_execute_branch_outage(instance_id, data))

    return {"id": instance_id, "processId": "branch-outage-response", "state": "ACTIVE"}


@app.post("/f5-vip-provisioning")
async def start_f5_provisioning(request: Request):
    """Execute the f5-vip-provisioning workflow."""
    data = await request.json()
    instance_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    instance = {
        "id": instance_id,
        "processId": "f5-vip-provisioning",
        "processName": "F5 VIP Provisioning",
        "state": "ACTIVE",
        "start": now,
        "end": None,
        "variables": data,
        "nodes": [],
        "error": None,
    }
    _instances[instance_id] = instance

    asyncio.create_task(_execute_f5_provisioning(instance_id, data))

    return {"id": instance_id, "processId": "f5-vip-provisioning", "state": "ACTIVE"}


@app.get("/management/processes/{process_id}/instances/{instance_id}")
async def get_instance(process_id: str, instance_id: str):
    inst = _instances.get(instance_id)
    if not inst:
        return {"error": "Instance not found", "instance_id": instance_id}
    return inst


@app.get("/q/health/ready")
@app.get("/q/health/live")
@app.get("/q/health/started")
async def health():
    return {"status": "UP"}


async def _execute_branch_outage(instance_id: str, data: dict):
    """Execute the branch-outage-response workflow steps."""
    inst = _instances[instance_id]
    threat_level = data.get("threatLevel", "MEDIUM")
    branch_id = data.get("branchId", "unknown")
    assessment = data.get("assessmentSummary", "")
    network_team = data.get("networkTeam", "network-ops")
    manager_phone = data.get("branchManagerPhone", "+1-555-0100")

    try:
        async with httpx.AsyncClient(base_url=MOCK_BACKEND, timeout=15.0) as client:
            _add_node(inst, "Classify Threat Level", "switch")

            if threat_level == "CRITICAL":
                _add_node(inst, "Critical Response", "operation")

                await client.post("/send", json={
                    "channel": network_team,
                    "message": f"CRITICAL: {branch_id} - {assessment}",
                    "severity": "critical",
                })
                _add_node(inst, "Send Teams Alert (CRITICAL)", "action")

                await client.post("/send", json={
                    "to": manager_phone,
                    "message": f"CRITICAL network threat: {branch_id}",
                })
                _add_node(inst, "Send SMS Alert (CRITICAL)", "action")

                resp = await client.post("/api/now/table/incident", json={
                    "short_description": f"CRITICAL network threat: {branch_id}",
                    "description": assessment,
                    "urgency": "1",
                    "impact": "1",
                    "assignment_group": network_team,
                })
                incident = resp.json().get("result", {})
                inst["variables"]["incidentId"] = incident.get("number", "INC-UNKNOWN")
                _add_node(inst, "Create P1 ServiceNow Incident", "action")

            elif threat_level == "HIGH":
                _add_node(inst, "High Response", "operation")

                await client.post("/send", json={
                    "channel": network_team,
                    "message": f"HIGH: {branch_id} - {assessment}",
                    "severity": "high",
                })
                _add_node(inst, "Send Teams Alert (HIGH)", "action")

                await client.post("/send", json={
                    "to": manager_phone,
                    "message": f"HIGH network threat: {branch_id}. Check backup connectivity.",
                })
                _add_node(inst, "Send SMS Alert (HIGH)", "action")

                resp = await client.post("/api/now/table/incident", json={
                    "short_description": f"HIGH network threat: {branch_id}",
                    "description": assessment,
                    "urgency": "2",
                    "impact": "2",
                    "assignment_group": network_team,
                })
                incident = resp.json().get("result", {})
                inst["variables"]["incidentId"] = incident.get("number", "INC-UNKNOWN")
                _add_node(inst, "Create P2 ServiceNow Incident", "action")

            else:
                _add_node(inst, "Medium Response", "operation")
                await client.post("/send", json={
                    "channel": network_team,
                    "message": f"MEDIUM: {branch_id} - {assessment}",
                    "severity": "medium",
                })
                _add_node(inst, "Send Teams Alert (MEDIUM)", "action")

            _add_node(inst, "Complete", "operation")
            incident_id = inst["variables"].get("incidentId", "N/A")
            inst["variables"]["result"] = {
                "message": f"Response executed for {branch_id} (threat: {threat_level})",
                "outputs": [
                    {"key": "Incident", "value": incident_id},
                    {"key": "Threat Level", "value": threat_level},
                ],
            }
            inst["state"] = "COMPLETED"
            inst["end"] = datetime.now(UTC).isoformat()
            logger.info("Workflow branch-outage-response %s completed", instance_id)

    except Exception as e:
        inst["state"] = "ERROR"
        inst["error"] = {"message": str(e)}
        inst["end"] = datetime.now(UTC).isoformat()
        logger.error("Workflow branch-outage-response %s failed: %s", instance_id, e)


async def _execute_f5_provisioning(instance_id: str, data: dict):
    """Execute the f5-vip-provisioning workflow steps."""
    inst = _instances[instance_id]
    vip_name = data.get("vipName", "unknown")
    assigned_ip = data.get("assignedIp", "0.0.0.0")
    pool_members = data.get("poolMembers", "")
    pool_name = data.get("poolName", "default-pool")
    request_id = data.get("requestId", "REQ-UNKNOWN")

    try:
        async with httpx.AsyncClient(base_url=MOCK_BACKEND, timeout=15.0) as client:
            resp = await client.post("/mgmt/tm/ltm/virtual", json={
                "name": vip_name,
                "destination": f"{assigned_ip}:443",
                "pool": pool_name,
            })
            inst["variables"]["f5ConfigResult"] = resp.json()
            _add_node(inst, "Configure F5 VIP", "operation")

            resp = await client.post("/checks", json={
                "vipIp": assigned_ip,
                "poolMembers": pool_members,
            })
            connectivity = resp.json()
            inst["variables"]["connectivityResult"] = connectivity
            _add_node(inst, "Run Connectivity Checks", "operation")

            _add_node(inst, "Check Connectivity Result", "switch")

            if connectivity.get("allHealthy"):
                await client.patch(f"/api/now/table/sc_request/{request_id}", json={
                    "status": "pending_approval",
                    "evidence": data.get("validationEvidence", ""),
                    "connectivityResult": connectivity,
                })
                _add_node(inst, "Submit Evidence to ServiceNow", "operation")

                inst["variables"]["result"] = {
                    "message": f"VIP {vip_name} provisioned successfully",
                    "outputs": [
                        {"key": "VIP IP", "value": assigned_ip},
                        {"key": "Request ID", "value": request_id},
                    ],
                }
                _add_node(inst, "Set Success Output", "operation")
            else:
                inst["variables"]["result"] = {
                    "message": f"VIP provisioning failed for {vip_name}"
                }
                _add_node(inst, "Notify Connectivity Failed", "operation")

            inst["state"] = "COMPLETED"
            inst["end"] = datetime.now(UTC).isoformat()
            logger.info("Workflow f5-vip-provisioning %s completed", instance_id)

    except Exception as e:
        inst["state"] = "ERROR"
        inst["error"] = {"message": str(e)}
        inst["end"] = datetime.now(UTC).isoformat()
        logger.error("Workflow f5-vip-provisioning %s failed: %s", instance_id, e)


def _add_node(inst: dict, name: str, node_type: str):
    now = datetime.now(UTC).isoformat()
    inst["nodes"].append({
        "name": name,
        "type": node_type,
        "enter": now,
        "exit": now,
    })

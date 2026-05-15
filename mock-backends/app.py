"""Workflow backend services.

Provides HTTP endpoints for services called by SonataFlow workflows.
ServiceNow calls are proxied to the real PDI instance.
Teams/SMS/F5/connectivity remain mock.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflow-backends")

SNOW_URL = os.environ.get("SERVICENOW_URL", "")
SNOW_USER = os.environ.get("SERVICENOW_USERNAME", "admin")
SNOW_PASS = os.environ.get("SERVICENOW_PASSWORD", "")

app = FastAPI(title="Workflow Backend Services")


@app.post("/send")
async def send_notification(request: Request):
    """Teams / SMS notification endpoint (mock)."""
    body = await request.json()
    logger.info("Notification sent: %s", json.dumps(body, indent=2))
    return {"status": "sent", "timestamp": datetime.now(UTC).isoformat()}


@app.post("/api/now/table/incident")
async def create_incident(request: Request):
    """ServiceNow create incident -- proxied to real PDI if credentials available."""
    body = await request.json()

    if SNOW_PASS:
        try:
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                resp = await client.post(
                    f"{SNOW_URL}/api/now/table/incident",
                    json=body,
                    auth=(SNOW_USER, SNOW_PASS),
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    result = data.get("result", {})
                    logger.info("REAL ServiceNow incident created: %s", result.get("number", "unknown"))
                    return data
                else:
                    logger.warning("ServiceNow API error %d, falling back to mock", resp.status_code)
        except Exception as e:
            logger.warning("ServiceNow proxy failed (%s), falling back to mock", e)

    incident_number = f"INC{datetime.now(UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    logger.info("Mock incident created: %s — %s", incident_number, body.get("short_description", ""))
    return {
        "result": {
            "sys_id": uuid.uuid4().hex,
            "number": incident_number,
            "state": "new",
            "short_description": body.get("short_description", ""),
        }
    }


@app.patch("/api/now/table/sc_request/{request_id}")
async def update_ticket(request_id: str, request: Request):
    """ServiceNow update ticket (mock)."""
    body = await request.json()
    logger.info("ServiceNow ticket %s updated: status=%s", request_id, body.get("status", "unknown"))
    return {"result": {"sys_id": request_id, "state": body.get("status", "updated")}}


@app.post("/mgmt/tm/ltm/virtual")
async def configure_vip(request: Request):
    """F5 BIG-IP configure VIP (mock)."""
    body = await request.json()
    logger.info("F5 VIP configured: name=%s destination=%s", body.get("name", ""), body.get("destination", ""))
    return {"name": body.get("name", ""), "status": "available", "destination": body.get("destination", "")}


@app.post("/checks")
async def run_connectivity_checks(request: Request):
    """Connectivity check service (mock)."""
    body = await request.json()
    logger.info("Connectivity checks for VIP %s", body.get("vipIp", ""))
    return {"allHealthy": True, "vipIp": body.get("vipIp", ""), "checks": [
        {"target": body.get("vipIp", ""), "protocol": "tcp/443", "status": "healthy", "latency_ms": 12},
    ]}


@app.get("/health")
async def health():
    return {"status": "ok"}

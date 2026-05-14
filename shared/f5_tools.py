"""Mock tools for the F5 VIP Provisioning agent.

Simulates Infoblox DNS, F5 BIG-IP, ServiceNow, and network connectivity
systems. In production, these would call real APIs through MCP servers.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_REQUESTS: dict[str, dict[str, Any]] = {
    "REQ-2025-0847": {
        "request_id": "REQ-2025-0847",
        "type": "f5_vip_provision",
        "status": "dns_assigned",
        "environment": "production",
        "application": "online-banking-api",
        "requested_by": "platform-team",
        "vip_name": "vs-onlinebanking-prod-443",
        "pool_name": "pool-onlinebanking-prod",
        "pool_members": ["10.120.50.11:8443", "10.120.50.12:8443", "10.120.50.13:8443"],
        "protocol": "HTTPS",
        "port": 443,
        "health_monitor": "/Common/https_head_f5",
        "persistence": "cookie",
        "ssl_profile": "clientssl-onlinebanking",
        "created_at": "2025-05-12T09:00:00Z",
    },
    "REQ-2025-0903": {
        "request_id": "REQ-2025-0903",
        "type": "f5_vip_provision",
        "status": "dns_assigned",
        "environment": "staging",
        "application": "mobile-gateway",
        "requested_by": "platform-team",
        "vip_name": "vs-mobilegw-staging-443",
        "pool_name": "pool-mobilegw-staging",
        "pool_members": ["10.130.20.5:8443", "10.130.20.6:8443"],
        "protocol": "HTTPS",
        "port": 443,
        "health_monitor": "/Common/https_head_f5",
        "persistence": "source_addr",
        "ssl_profile": "clientssl-mobilegw",
        "created_at": "2025-05-13T14:30:00Z",
    },
}

_MOCK_DNS: dict[str, dict[str, Any]] = {
    "REQ-2025-0847": {
        "request_id": "REQ-2025-0847",
        "hostname": "onlinebanking.prod.internal.bank.com",
        "assigned_ip": "10.120.100.25",
        "dns_server": "infoblox-prod.internal.bank.com",
        "subnet": "10.120.100.0/24",
        "gateway": "10.120.100.1",
        "vlan": "VLAN-120",
        "assigned_by": "dns-team",
        "assigned_at": "2025-05-13T10:15:00Z",
        "reverse_dns": "25.100.120.10.in-addr.arpa",
        "ttl": 3600,
    },
    "REQ-2025-0903": {
        "request_id": "REQ-2025-0903",
        "hostname": "mobilegw-stg.prod.internal.bank.com",
        "assigned_ip": "10.120.100.30",
        "dns_server": "infoblox-prod.internal.bank.com",
        "subnet": "10.120.100.0/24",
        "gateway": "10.120.100.1",
        "vlan": "VLAN-120",
        "assigned_by": "dns-team",
        "assigned_at": "2025-05-14T08:00:00Z",
        "reverse_dns": "30.100.120.10.in-addr.arpa",
        "ttl": 3600,
    },
}

_NAMING_CONVENTIONS = {
    "production": {
        "hostname_pattern": "{app}.prod.internal.bank.com",
        "subnet_prefix": "10.120.",
        "vlan_range": ["VLAN-120", "VLAN-121", "VLAN-122"],
        "ip_range": "10.120.100.0/24 or 10.120.101.0/24",
    },
    "staging": {
        "hostname_pattern": "{app}.stg.internal.bank.com",
        "subnet_prefix": "10.130.",
        "vlan_range": ["VLAN-130", "VLAN-131"],
        "ip_range": "10.130.20.0/24 or 10.130.21.0/24",
    },
    "development": {
        "hostname_pattern": "{app}.dev.internal.bank.com",
        "subnet_prefix": "10.140.",
        "vlan_range": ["VLAN-140"],
        "ip_range": "10.140.10.0/24",
    },
}

_MOCK_SUBNET_INFO: dict[str, dict[str, Any]] = {
    "10.120.100.0/24": {
        "subnet": "10.120.100.0/24",
        "environment": "production",
        "purpose": "F5 VIP addresses - production",
        "vlan": "VLAN-120",
        "gateway": "10.120.100.1",
        "available_ips": 47,
        "total_ips": 254,
    },
    "10.130.20.0/24": {
        "subnet": "10.130.20.0/24",
        "environment": "staging",
        "purpose": "Application servers - staging",
        "vlan": "VLAN-130",
        "gateway": "10.130.20.1",
        "available_ips": 112,
        "total_ips": 254,
    },
}

_MOCK_HISTORICAL: list[dict[str, Any]] = [
    {
        "request_id": "REQ-2025-0712",
        "hostname": "payments.prod.internal.bank.com",
        "assigned_ip": "10.120.100.20",
        "environment": "production",
        "result": "success",
        "issues": [],
    },
    {
        "request_id": "REQ-2025-0698",
        "hostname": "auth-svc.prod.internal.bank.com",
        "assigned_ip": "10.130.20.15",
        "environment": "production",
        "result": "failed_validation",
        "issues": ["IP 10.130.20.15 is in staging subnet (10.130.x.x) but request is for production"],
    },
    {
        "request_id": "REQ-2025-0655",
        "hostname": "reporting-stg.prod.internal.bank.com",
        "assigned_ip": "10.130.20.10",
        "environment": "staging",
        "result": "failed_validation",
        "issues": ["Hostname contains 'stg' but DNS suffix is .prod.internal -- should be .stg.internal"],
    },
]


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------


def get_servicenow_request(request_id: str) -> str:
    """Get details of an F5 VIP provisioning request from ServiceNow.

    Args:
        request_id: ServiceNow request ID (e.g. 'REQ-2025-0847').

    Returns:
        JSON string with request details including environment,
        application, VIP configuration, and pool members.
    """
    req = _MOCK_REQUESTS.get(request_id)
    if req is None:
        return json.dumps({"error": f"Request '{request_id}' not found"})
    return json.dumps(req, indent=2)


def get_dns_assignment(request_id: str) -> str:
    """Get the DNS/IP assignment from Infoblox for a provisioning request.

    Args:
        request_id: ServiceNow request ID.

    Returns:
        JSON string with assigned hostname, IP, subnet, VLAN,
        and the DNS server that made the assignment.
    """
    dns = _MOCK_DNS.get(request_id)
    if dns is None:
        return json.dumps({"error": f"No DNS assignment found for '{request_id}'"})
    return json.dumps(dns, indent=2)


def get_naming_conventions(environment: str) -> str:
    """Get the expected naming conventions for an environment.

    Args:
        environment: Target environment (production, staging, development).

    Returns:
        JSON string with expected hostname pattern, subnet prefix,
        VLAN range, and IP range for the environment.
    """
    conv = _NAMING_CONVENTIONS.get(environment)
    if conv is None:
        return json.dumps({"error": f"No naming conventions for environment '{environment}'"})
    return json.dumps({"environment": environment, **conv}, indent=2)


def get_subnet_info(ip_address: str) -> str:
    """Look up subnet information for an IP address.

    Args:
        ip_address: IP address to look up.

    Returns:
        JSON string with subnet, environment, purpose, VLAN,
        and available IP count.
    """
    octets = ip_address.split(".")
    if len(octets) == 4:
        subnet_key = f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
        info = _MOCK_SUBNET_INFO.get(subnet_key)
        if info:
            return json.dumps(info, indent=2)
    return json.dumps({"ip": ip_address, "error": "Subnet information not found"})


def get_historical_assignments(environment: str = "", limit: int = 10) -> str:
    """Get historical DNS/IP assignments for comparison.

    Args:
        environment: Filter by environment. Leave empty for all.
        limit: Maximum number of results.

    Returns:
        JSON string with past assignments including any validation
        issues that were found.
    """
    results = _MOCK_HISTORICAL
    if environment:
        results = [h for h in results if h["environment"] == environment]
    return json.dumps({"assignments": results[:limit], "total": len(results)}, indent=2)


def get_f5_config(vip_name: str) -> str:
    """Get the current F5 VIP configuration (after provisioning).

    Args:
        vip_name: VIP name (e.g. 'vs-onlinebanking-prod-443').

    Returns:
        JSON string with VIP configuration including IP, port,
        pool members, health monitor, and SSL profile.
    """
    for req in _MOCK_REQUESTS.values():
        if req["vip_name"] == vip_name:
            dns = _MOCK_DNS.get(req["request_id"], {})
            return json.dumps(
                {
                    "vip_name": vip_name,
                    "vip_ip": dns.get("assigned_ip", "unknown"),
                    "port": req["port"],
                    "protocol": req["protocol"],
                    "pool_name": req["pool_name"],
                    "pool_members": req["pool_members"],
                    "health_monitor": req["health_monitor"],
                    "persistence": req["persistence"],
                    "ssl_profile": req["ssl_profile"],
                    "status": "active",
                },
                indent=2,
            )
    return json.dumps({"error": f"VIP '{vip_name}' not found"})


def run_connectivity_check(vip_ip: str, pool_members: str) -> str:
    """Run connectivity checks against VIP IP and pool members.

    Args:
        vip_ip: VIP IP address to test.
        pool_members: Comma-separated list of pool member addresses (ip:port).

    Returns:
        JSON string with connectivity test results for VIP and each pool member.
    """
    members = [m.strip() for m in pool_members.split(",")]
    results = {
        "vip_check": {"ip": vip_ip, "reachable": True, "latency_ms": 2},
        "pool_checks": [],
    }
    for member in members:
        results["pool_checks"].append({"member": member, "reachable": True, "latency_ms": 3, "health": "UP"})
    results["all_healthy"] = True
    return json.dumps(results, indent=2)


def submit_evidence_package(request_id: str, evidence: str) -> str:
    """Submit the evidence package to ServiceNow for approval.

    Args:
        request_id: ServiceNow request ID.
        evidence: JSON-formatted evidence summary from the agent.

    Returns:
        JSON string confirming the evidence was attached and approval requested.
    """
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return json.dumps(
        {
            "status": "evidence_submitted",
            "request_id": request_id,
            "submitted_at": now,
            "approval_status": "pending_f5_team_review",
            "evidence_length": len(evidence),
            "next_step": "F5 network team will review and approve/reject within SLA",
        },
        indent=2,
    )

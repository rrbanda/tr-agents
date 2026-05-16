"""Tools for the Branch Network Monitoring agent.

Weather alerts use the real NWS API (https://api.weather.gov -- free, public).
Power outage data uses the real Duke Energy ArcGIS API (public, no auth).
ISP status and equipment health use mock data (would need internal/paid APIs).
Branch inventory uses mock data (would be an internal database).

Each tool tries the real API first and falls back to mock data if unreachable.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

_NWS_API_BASE = "https://api.weather.gov"
_NWS_HEADERS = {"User-Agent": "tr-agents/1.0 (network-monitoring-agent)", "Accept": "application/geo+json"}

_DUKE_ENERGY_API = (
    "https://services3.arcgis.com/oX5r75R7mapdoI2F/ArcGIS/rest/services/"
    "Duke_Energy_Distribution_Outages_Public/FeatureServer/0/query"
)

# ---------------------------------------------------------------------------
# Mock data -- internally consistent across all tools
# ---------------------------------------------------------------------------

_MOCK_BRANCHES: dict[str, dict[str, Any]] = {
    "BR-4471": {
        "branch_id": "BR-4471",
        "name": "South Tryon Street Branch",
        "city": "Charlotte",
        "state": "NC",
        "zip": "28202",
        "county": "Mecklenburg",
        "isp_primary": "AT&T Business",
        "isp_backup": "Spectrum Enterprise",
        "equipment": ["Cisco ISR 4331", "Cisco Catalyst 9200", "F5 BIG-IP LTM"],
        "atm_count": 2,
        "staff_count": 12,
        "manager": "Sarah Chen",
        "manager_phone": "+1-704-555-0147",
        "network_team": "charlotte-netops",
    },
    "BR-4485": {
        "branch_id": "BR-4485",
        "name": "Independence Boulevard Branch",
        "city": "Charlotte",
        "state": "NC",
        "zip": "28205",
        "county": "Mecklenburg",
        "isp_primary": "AT&T Business",
        "isp_backup": "Comcast Business",
        "equipment": ["Cisco ISR 4321", "Cisco Catalyst 9200"],
        "atm_count": 1,
        "staff_count": 8,
        "manager": "James Rodriguez",
        "manager_phone": "+1-704-555-0293",
        "network_team": "charlotte-netops",
    },
    "BR-5512": {
        "branch_id": "BR-5512",
        "name": "Peachtree Street Branch",
        "city": "Atlanta",
        "state": "GA",
        "zip": "30308",
        "county": "Fulton",
        "isp_primary": "Comcast Business",
        "isp_backup": "AT&T Business",
        "equipment": ["Cisco ISR 4331", "Cisco Catalyst 9200", "F5 BIG-IP LTM"],
        "atm_count": 3,
        "staff_count": 15,
        "manager": "Maria Washington",
        "manager_phone": "+1-404-555-0381",
        "network_team": "atlanta-netops",
    },
    "ATM-28202-A": {
        "branch_id": "ATM-28202-A",
        "name": "ATM Cluster - Uptown Charlotte",
        "city": "Charlotte",
        "state": "NC",
        "zip": "28202",
        "county": "Mecklenburg",
        "isp_primary": "AT&T Business",
        "isp_backup": "none",
        "equipment": ["Cisco ISR 1100", "NCR SelfServ 80"],
        "atm_count": 4,
        "staff_count": 0,
        "manager": "Sarah Chen",
        "manager_phone": "+1-704-555-0147",
        "network_team": "charlotte-netops",
    },
}

_MOCK_WEATHER: dict[str, list[dict[str, Any]]] = {
    "Mecklenburg": [
        {
            "event": "Severe Thunderstorm Warning",
            "severity": "severe",
            "certainty": "observed",
            "onset": "2025-05-14T14:00:00-04:00",
            "expires": "2025-05-14T19:00:00-04:00",
            "headline": "Severe Thunderstorm Warning for Mecklenburg County until 7 PM EDT",
            "description": (
                "Severe thunderstorms with damaging winds up to 70 mph and large hail. "
                "Power outages likely. Flash flooding possible in low-lying areas."
            ),
            "affected_zones": ["NCZ071", "NCZ072"],
            "source": "NWS Weather Prediction Center",
        },
    ],
    "Fulton": [],
}

_MOCK_POWER: dict[str, dict[str, Any]] = {
    "28202": {
        "zip": "28202",
        "provider": "Duke Energy",
        "status": "active_outage",
        "customers_affected": 3200,
        "customers_total": 18500,
        "outage_start": "2025-05-14T13:45:00-04:00",
        "estimated_restoration": "2025-05-14T20:00:00-04:00",
        "cause": "Storm damage -- downed power lines on West Trade Street",
        "crew_dispatched": True,
    },
    "28205": {
        "zip": "28205",
        "provider": "Duke Energy",
        "status": "monitoring",
        "customers_affected": 0,
        "customers_total": 12300,
        "outage_start": None,
        "estimated_restoration": None,
        "cause": None,
        "crew_dispatched": False,
    },
    "30308": {
        "zip": "30308",
        "provider": "Georgia Power",
        "status": "normal",
        "customers_affected": 0,
        "customers_total": 22100,
        "outage_start": None,
        "estimated_restoration": None,
        "cause": None,
        "crew_dispatched": False,
    },
}

_MOCK_ISP: dict[str, dict[str, Any]] = {
    "AT&T Business:Charlotte": {
        "provider": "AT&T Business",
        "region": "Charlotte",
        "status": "degraded",
        "latency_ms": 145,
        "normal_latency_ms": 12,
        "packet_loss_pct": 4.2,
        "affected_services": ["MPLS", "DIA"],
        "incident_id": "ATT-INC-20250514-0892",
        "started_at": "2025-05-14T13:30:00-04:00",
        "description": "Elevated latency and packet loss in Charlotte metro area due to fiber damage",
    },
    "Spectrum Enterprise:Charlotte": {
        "provider": "Spectrum Enterprise",
        "region": "Charlotte",
        "status": "normal",
        "latency_ms": 8,
        "normal_latency_ms": 9,
        "packet_loss_pct": 0.0,
        "affected_services": [],
        "incident_id": None,
        "started_at": None,
        "description": "All services operating normally",
    },
    "Comcast Business:Charlotte": {
        "provider": "Comcast Business",
        "region": "Charlotte",
        "status": "normal",
        "latency_ms": 11,
        "normal_latency_ms": 10,
        "packet_loss_pct": 0.1,
        "affected_services": [],
        "incident_id": None,
        "started_at": None,
        "description": "All services operating normally",
    },
    "Comcast Business:Atlanta": {
        "provider": "Comcast Business",
        "region": "Atlanta",
        "status": "normal",
        "latency_ms": 9,
        "normal_latency_ms": 8,
        "packet_loss_pct": 0.0,
        "affected_services": [],
        "incident_id": None,
        "started_at": None,
        "description": "All services operating normally",
    },
}

_MOCK_EQUIPMENT: dict[str, dict[str, Any]] = {
    "BR-4471": {
        "branch_id": "BR-4471",
        "primary_link": {
            "status": "degraded",
            "latency_ms": 210,
            "normal_latency_ms": 8,
            "packet_loss_pct": 6.1,
            "uptime_hours": 2847,
            "provider": "AT&T Business",
        },
        "backup_link": {
            "status": "standby",
            "latency_ms": 9,
            "normal_latency_ms": 9,
            "packet_loss_pct": 0.0,
            "uptime_hours": 2847,
            "provider": "Spectrum Enterprise",
        },
        "router": {"status": "healthy", "cpu_pct": 34, "memory_pct": 52, "temperature_c": 42},
        "switch": {"status": "healthy", "port_errors": 0, "active_ports": 24},
        "ups_battery_pct": 85,
        "ups_runtime_minutes": 45,
        "last_check": "2025-05-14T14:02:00-04:00",
    },
    "BR-4485": {
        "branch_id": "BR-4485",
        "primary_link": {
            "status": "healthy",
            "latency_ms": 14,
            "normal_latency_ms": 10,
            "packet_loss_pct": 0.2,
            "uptime_hours": 4123,
            "provider": "AT&T Business",
        },
        "backup_link": {
            "status": "standby",
            "latency_ms": 11,
            "normal_latency_ms": 10,
            "packet_loss_pct": 0.0,
            "uptime_hours": 4123,
            "provider": "Comcast Business",
        },
        "router": {"status": "healthy", "cpu_pct": 22, "memory_pct": 41, "temperature_c": 38},
        "switch": {"status": "healthy", "port_errors": 0, "active_ports": 16},
        "ups_battery_pct": 92,
        "ups_runtime_minutes": 60,
        "last_check": "2025-05-14T14:02:00-04:00",
    },
    "BR-5512": {
        "branch_id": "BR-5512",
        "primary_link": {
            "status": "healthy",
            "latency_ms": 9,
            "normal_latency_ms": 8,
            "packet_loss_pct": 0.0,
            "uptime_hours": 6201,
            "provider": "Comcast Business",
        },
        "backup_link": {
            "status": "standby",
            "latency_ms": 10,
            "normal_latency_ms": 10,
            "packet_loss_pct": 0.0,
            "uptime_hours": 6201,
            "provider": "AT&T Business",
        },
        "router": {"status": "healthy", "cpu_pct": 28, "memory_pct": 45, "temperature_c": 40},
        "switch": {"status": "healthy", "port_errors": 0, "active_ports": 32},
        "ups_battery_pct": 98,
        "ups_runtime_minutes": 90,
        "last_check": "2025-05-14T14:02:00-04:00",
    },
    "ATM-28202-A": {
        "branch_id": "ATM-28202-A",
        "primary_link": {
            "status": "degraded",
            "latency_ms": 340,
            "normal_latency_ms": 15,
            "packet_loss_pct": 12.3,
            "uptime_hours": 1456,
            "provider": "AT&T Business",
        },
        "backup_link": None,
        "router": {"status": "warning", "cpu_pct": 78, "memory_pct": 71, "temperature_c": 51},
        "switch": None,
        "ups_battery_pct": 62,
        "ups_runtime_minutes": 20,
        "last_check": "2025-05-14T14:01:00-04:00",
    },
}

_MOCK_INCIDENTS: dict[str, list[dict[str, Any]]] = {
    "BR-4471": [
        {
            "incident_id": "INC-2025-03-0412",
            "date": "2025-03-12",
            "cause": "ISP fiber cut during construction",
            "duration_hours": 4.5,
            "resolution": "Failover to backup ISP, primary restored by ISP",
        },
        {
            "incident_id": "INC-2024-09-1847",
            "date": "2024-09-15",
            "cause": "Hurricane Helene -- power outage",
            "duration_hours": 18.0,
            "resolution": "Generator deployed, power restored by Duke Energy",
        },
    ],
    "ATM-28202-A": [
        {
            "incident_id": "INC-2025-01-0098",
            "date": "2025-01-22",
            "cause": "Ice storm -- power + ISP outage",
            "duration_hours": 8.0,
            "resolution": "ATMs offline until power restored. No backup ISP.",
        },
    ],
}


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------


def get_weather_alerts(state: str, county: str) -> str:
    """Get active weather alerts from the National Weather Service for a county.

    Calls the real NWS API at https://api.weather.gov/alerts/active.
    Falls back to mock data if the API is unreachable.

    Args:
        state: Two-letter state code (e.g. 'NC', 'GA').
        county: County name (e.g. 'Mecklenburg', 'Fulton').

    Returns:
        JSON string with active weather alerts including severity,
        timing, and description.
    """
    try:
        resp = requests.get(
            f"{_NWS_API_BASE}/alerts/active",
            params={"area": state, "status": "actual", "message_type": "alert"},
            headers=_NWS_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])

        alerts = []
        county_lower = county.lower()
        for f in features:
            props = f.get("properties", {})
            area_desc = (props.get("areaDesc") or "").lower()
            if county_lower in area_desc:
                alerts.append({
                    "event": props.get("event", ""),
                    "severity": (props.get("severity") or "unknown").lower(),
                    "certainty": (props.get("certainty") or "unknown").lower(),
                    "onset": props.get("onset", ""),
                    "expires": props.get("expires", ""),
                    "headline": props.get("headline", ""),
                    "description": (props.get("description") or "")[:500],
                    "source": "NWS API (live)",
                })

        return json.dumps(
            {"state": state, "county": county, "alert_count": len(alerts), "alerts": alerts, "source": "nws_api_live"},
            indent=2,
        )
    except Exception as exc:
        logger.warning("NWS API unavailable (%s), using mock data", exc)
        alerts = _MOCK_WEATHER.get(county, [])
        return json.dumps(
            {
                "state": state,
                "county": county,
                "alert_count": len(alerts),
                "alerts": alerts,
                "source": "mock_fallback",
            },
            indent=2,
        )


def get_power_outage_status(zip_code: str) -> str:
    """Get power outage status from Duke Energy's public ArcGIS outage API.

    Calls the real Duke Energy API at services3.arcgis.com.
    Falls back to mock data if the API is unreachable.

    Args:
        zip_code: 5-digit ZIP code.

    Returns:
        JSON string with outage status, customers affected,
        estimated restoration time, and cause.
    """
    try:
        resp = requests.get(
            _DUKE_ENERGY_API,
            params={
                "where": f"ZIP_CODE='{zip_code}'",
                "outFields": "COUNTY,CUSTOMERS_OUT,TOTAL_CUSTOMERS,CAUSE,ETR,ZIP_CODE",
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])

        if features:
            attrs = features[0].get("attributes", {})
            customers_out = attrs.get("CUSTOMERS_OUT", 0) or 0
            total = attrs.get("TOTAL_CUSTOMERS", 1) or 1
            status = "active_outage" if customers_out > 0 else "normal"
            return json.dumps(
                {
                    "zip": zip_code,
                    "provider": "Duke Energy",
                    "status": status,
                    "customers_affected": customers_out,
                    "customers_total": total,
                    "cause": attrs.get("CAUSE", "Unknown"),
                    "estimated_restoration": attrs.get("ETR"),
                    "county": attrs.get("COUNTY", ""),
                    "source": "duke_energy_api_live",
                },
                indent=2,
            )

        # No data for this ZIP in Duke Energy territory
        mock = _MOCK_POWER.get(zip_code)
        if mock:
            mock["source"] = "mock_fallback"
            return json.dumps(mock, indent=2)
        return json.dumps(
            {"zip": zip_code, "status": "no_data", "message": "ZIP not in Duke Energy territory", "source": "no_match"}
        )

    except Exception as exc:
        logger.warning("Duke Energy API unavailable (%s), using mock data", exc)
        status = _MOCK_POWER.get(zip_code)
        if status is None:
            return json.dumps({"zip": zip_code, "status": "no_data", "source": "mock_fallback"})
        status["source"] = "mock_fallback"
        return json.dumps(status, indent=2)


def get_isp_status(provider: str, region: str) -> str:
    """Get ISP service status for a provider in a region.

    Args:
        provider: ISP name (e.g. 'AT&T Business', 'Spectrum Enterprise').
        region: Metro region (e.g. 'Charlotte', 'Atlanta').

    Returns:
        JSON string with service status, latency, packet loss,
        and any active incidents.
    """
    key = f"{provider}:{region}"
    status = _MOCK_ISP.get(key)
    if status is None:
        return json.dumps({"provider": provider, "region": region, "status": "no_data"})
    return json.dumps(status, indent=2)


def get_equipment_health(branch_id: str) -> str:
    """Get network equipment health from SNMP/monitoring for a branch or ATM site.

    Args:
        branch_id: Branch or ATM identifier (e.g. 'BR-4471', 'ATM-28202-A').

    Returns:
        JSON string with link status, latency, router/switch health,
        UPS battery level, and last check timestamp.
    """
    health = _MOCK_EQUIPMENT.get(branch_id)
    if health is None:
        return json.dumps({"branch_id": branch_id, "error": "No monitoring data available"})
    return json.dumps(health, indent=2)


_STATE_ALIASES: dict[str, str] = {
    "north carolina": "nc", "south carolina": "sc",
    "georgia": "ga", "virginia": "va", "tennessee": "tn",
    "florida": "fl", "texas": "tx", "new york": "ny",
    "california": "ca", "ohio": "oh", "pennsylvania": "pa",
    "maryland": "md", "alabama": "al", "mississippi": "ms",
}


def get_branch_inventory(region: str = "") -> str:
    """Get branch and ATM inventory, optionally filtered by region.

    Args:
        region: City, state name, or state abbreviation to filter by.
                Leave empty for all branches.

    Returns:
        JSON string with branch details including location, ISP,
        equipment, and contact information.
    """
    results = []
    normalized = region.lower().strip()
    normalized = _STATE_ALIASES.get(normalized, normalized)
    for branch in _MOCK_BRANCHES.values():
        if normalized and normalized not in (
            branch["city"].lower(), branch["state"].lower()
        ):
            continue
        results.append(branch)
    return json.dumps({"total": len(results), "branches": results}, indent=2)


def get_historical_incidents(branch_id: str) -> str:
    """Get past network incidents for a branch or ATM site.

    Args:
        branch_id: Branch or ATM identifier.

    Returns:
        JSON string with past incidents including cause,
        duration, and resolution.
    """
    incidents = _MOCK_INCIDENTS.get(branch_id, [])
    return json.dumps({"branch_id": branch_id, "incident_count": len(incidents), "incidents": incidents}, indent=2)


def send_alert(recipients: str, severity: str, message: str) -> str:
    """Send an alert notification to network team or branch managers.

    Args:
        recipients: Comma-separated list of recipients (team names or phone numbers).
        severity: Alert severity (critical, high, medium, low).
        message: Alert message text.

    Returns:
        JSON string confirming the alert was sent.
    """
    logger.info("Alert sent: severity=%s recipients=%s", severity, recipients)
    return json.dumps({
        "status": "sent",
        "severity": severity,
        "recipients": recipients,
        "message": message[:200],
        "delivery": "Teams + SMS for critical/high, Teams only for medium/low",
    })


def create_preemptive_incident(branch_id: str, threat_level: str, assessment: str) -> str:
    """Create a preemptive ServiceNow incident based on threat assessment.

    Args:
        branch_id: Affected branch or ATM identifier.
        threat_level: Assessed threat level (critical, high, medium, low).
        assessment: Agent's threat assessment summary.

    Returns:
        JSON string with the created incident details.
    """
    logger.info("Preemptive incident created: branch=%s threat=%s", branch_id, threat_level)
    return json.dumps({
        "status": "created",
        "incident_id": f"INC-2025-05-{branch_id[-4:]}",
        "branch_id": branch_id,
        "threat_level": threat_level,
        "type": "preemptive",
        "assessment": assessment[:500],
        "assigned_to": _MOCK_BRANCHES.get(branch_id, {}).get("network_team", "unassigned"),
        "priority": "P1" if threat_level == "critical" else "P2" if threat_level == "high" else "P3",
    })

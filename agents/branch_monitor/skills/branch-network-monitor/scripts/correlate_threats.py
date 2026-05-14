#!/usr/bin/env python3
"""Threat correlation scoring engine.

Computes a deterministic threat score per branch by weighting signals
from weather, power, ISP, and equipment data. Called by the agent via
run_skill_script to ensure consistent, non-hallucinated scoring.

Input: JSON on stdin with keys: weather, power, isp, equipment
Output: JSON on stdout with threat_score and threat_level per branch
"""

import json
import sys


def _weather_score(alerts: list[dict]) -> int:
    """Score weather threat (0-40 points)."""
    if not alerts:
        return 0
    max_severity = max(
        {"extreme": 40, "severe": 30, "moderate": 15, "minor": 5}.get(a.get("severity", ""), 0)
        for a in alerts
    )
    return max_severity


def _power_score(power: dict) -> int:
    """Score power outage threat (0-30 points)."""
    status = power.get("status", "normal")
    if status == "active_outage":
        affected_pct = power.get("customers_affected", 0) / max(power.get("customers_total", 1), 1)
        if affected_pct > 0.1:
            return 30
        return 20
    if status == "monitoring":
        return 10
    return 0


def _isp_score(isp: dict) -> int:
    """Score ISP degradation threat (0-20 points)."""
    status = isp.get("status", "normal")
    if status == "outage":
        return 20
    if status == "degraded":
        packet_loss = isp.get("packet_loss_pct", 0)
        if packet_loss > 5:
            return 18
        if packet_loss > 1:
            return 12
        return 8
    return 0


def _equipment_score(equip: dict) -> int:
    """Score equipment health threat (0-10 points)."""
    score = 0
    primary = equip.get("primary_link", {})
    if primary.get("status") == "degraded":
        score += 4
    if primary.get("status") == "down":
        score += 8

    backup = equip.get("backup_link")
    if backup is None or backup.get("status") == "down":
        score += 2

    ups = equip.get("ups_battery_pct", 100)
    if ups < 30:
        score += 3
    elif ups < 50:
        score += 1

    router = equip.get("router", {})
    if router.get("cpu_pct", 0) > 80 or router.get("temperature_c", 0) > 55:
        score += 1

    return min(score, 10)


def _threat_level(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def correlate(data: dict) -> dict:
    """Compute threat scores for all branches in the input data."""
    results = []

    for branch_id, branch_data in data.get("branches", {}).items():
        w_score = _weather_score(branch_data.get("weather", []))
        p_score = _power_score(branch_data.get("power", {}))
        i_score = _isp_score(branch_data.get("isp", {}))
        e_score = _equipment_score(branch_data.get("equipment", {}))

        total = w_score + p_score + i_score + e_score

        results.append({
            "branch_id": branch_id,
            "threat_score": total,
            "threat_level": _threat_level(total),
            "breakdown": {
                "weather": w_score,
                "power": p_score,
                "isp": i_score,
                "equipment": e_score,
            },
        })

    results.sort(key=lambda x: x["threat_score"], reverse=True)
    return {"assessments": results}


if __name__ == "__main__":
    input_data = json.load(sys.stdin)
    output = correlate(input_data)
    json.dump(output, sys.stdout, indent=2)

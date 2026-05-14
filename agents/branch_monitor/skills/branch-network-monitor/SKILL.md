---
name: branch-network-monitor
description: Monitors branch and ATM network health by correlating weather, power, ISP, and equipment data to proactively detect potential outages. Assigns threat levels per location and recommends response actions.
compatibility: Requires access to weather alerts, power outage feeds, ISP status, SNMP monitoring, and branch inventory APIs.
metadata:
  author: network-ops
  version: "1.0"
  tags: monitoring, network, proactive, branch, atm, correlation
allowed-tools: run_skill_script
---

# Branch Network Monitoring Instructions

When asked to assess branch network health, follow this methodology:

## Step 1: Get Branch Inventory

Use `get_branch_inventory` to identify branches and ATMs in the target region. Note each location's:
- ZIP code (for power outage lookup)
- County (for weather alerts)
- Primary and backup ISP
- Equipment list

## Step 2: Check Weather Alerts

For each unique county in the branch inventory, use `get_weather_alerts` to check for active NWS alerts. Note:
- Severity: extreme, severe, moderate, minor
- Timing: is the event happening now or approaching?
- Impact type: wind (power lines), flooding (facility), ice (equipment)

## Step 3: Check Power Status

For each unique ZIP code, use `get_power_outage_status`. Note:
- Active outage vs monitoring vs normal
- Number of customers affected (scale of impact)
- Estimated restoration time
- Whether crews are dispatched

## Step 4: Check ISP Status

For each unique ISP+region combination, use `get_isp_status`. Note:
- Degraded vs normal
- Latency vs normal baseline
- Packet loss percentage
- Any active incidents

## Step 5: Check Equipment Health

For each branch/ATM, use `get_equipment_health`. Note:
- Primary link status and latency
- Backup link availability
- Router/switch health
- UPS battery level and runtime

## Step 6: Compute Threat Score

Use `run_skill_script` to execute `scripts/correlate_threats.py` with the collected data. The script computes a threat score per branch based on:
- Weather severity weight (0-40 points)
- Power outage weight (0-30 points)
- ISP degradation weight (0-20 points)
- Equipment health weight (0-10 points)

Threat levels: CRITICAL (80+), HIGH (60-79), MEDIUM (40-59), LOW (0-39)

## Step 7: Check Historical Context

For branches with HIGH or CRITICAL threats, use `get_historical_incidents` to check if this location has experienced similar issues before. Historical patterns help predict duration and required response.

## Step 8: Generate Assessment

For each affected location, present:
```json
{
  "branch_id": "...",
  "branch_name": "...",
  "threat_level": "HIGH",
  "threat_score": 72,
  "contributing_factors": [
    {"source": "weather", "finding": "...", "weight": 35},
    {"source": "power", "finding": "...", "weight": 25},
    {"source": "isp", "finding": "...", "weight": 12},
    {"source": "equipment", "finding": "...", "weight": 0}
  ],
  "historical_context": "Similar event in Sep 2024 lasted 18 hours",
  "recommended_actions": [
    "Alert charlotte-netops team",
    "Verify backup ISP link is active",
    "Notify branch manager Sarah Chen"
  ]
}
```

## Step 9: Execute Response via RHDH Orchestrator

For HIGH/CRITICAL threats:
- Use `trigger_workflow` with workflow_id `branch-outage-response`
- Pass the threat assessment as input: branchId, threatLevel, threatScore, assessmentSummary, networkTeam, branchManagerPhone, recommendedActions
- The RHDH Orchestrator workflow handles the deterministic response steps: Teams alerts, SMS notifications, ServiceNow incident creation, and field tech dispatch
- Use `get_workflow_status` to confirm the response completed
- You do NOT need to call send_alert or create_preemptive_incident individually -- the workflow orchestrates all response actions

For MEDIUM threats:
- Use `send_alert` to notify the network team only (no workflow needed)
- Do not create a ticket unless requested

For LOW threats:
- Log the assessment but do not alert

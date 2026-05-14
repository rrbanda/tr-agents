# Threat Assessment Methodology

## Scoring Weights

The threat score is computed by `scripts/correlate_threats.py` using four weighted components:

| Component | Max Points | What It Measures |
|-----------|-----------|-----------------|
| Weather | 40 | Severity of active weather alerts in the branch's county |
| Power | 30 | Utility outage status in the branch's ZIP code |
| ISP | 20 | Service degradation for the branch's primary ISP |
| Equipment | 10 | Local equipment health from SNMP monitoring |

Total score range: 0-100

## Threat Levels

| Level | Score Range | Response |
|-------|-----------|----------|
| CRITICAL | 80-100 | Immediate alert to network team + branch manager, preemptive incident ticket, pre-stage field tech |
| HIGH | 60-79 | Alert network team + branch manager, preemptive incident ticket, verify backup links |
| MEDIUM | 40-59 | Alert network team only, monitor closely |
| LOW | 0-39 | Log assessment, no action needed |

## Correlation Patterns

Known cascading failure patterns:

1. **Storm -> Power -> ISP cascade**: Severe weather causes power outage, which causes ISP equipment failure. Expected delay between weather onset and ISP degradation: 30-90 minutes.

2. **ISP fiber cut**: Single-point failure affecting all branches on that ISP in the region. Usually repaired within 4-8 hours. Branches with backup ISP fail over automatically.

3. **Equipment aging**: Branches with equipment older than 5 years have 3x higher failure rates during weather events. Check equipment age in inventory.

4. **No-backup sites**: ATM clusters and smaller branches often lack a backup ISP link. These are highest priority during ISP outages.

## Escalation Matrix

| Threat Level | Network Team | Branch Manager | ServiceNow | Field Tech |
|-------------|-------------|---------------|------------|-----------|
| CRITICAL | Immediate (Teams + Phone) | Immediate (SMS + Phone) | P1 auto-create | Pre-stage |
| HIGH | Immediate (Teams) | SMS notification | P2 auto-create | On standby |
| MEDIUM | Teams notification | None | None | None |
| LOW | None | None | None | None |

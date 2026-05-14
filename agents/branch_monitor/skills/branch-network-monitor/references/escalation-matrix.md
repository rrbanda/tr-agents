# Escalation Matrix

## Team Contact Rules

| Team | Channel | When to Alert |
|------|---------|-------------|
| Regional Network Ops | Microsoft Teams channel | MEDIUM, HIGH, CRITICAL |
| Branch Manager | SMS + Teams | HIGH, CRITICAL |
| Network Engineering Lead | Phone call | CRITICAL only |
| VP Infrastructure | Email summary | CRITICAL lasting > 2 hours |

## ServiceNow Ticket Rules

| Threat Level | Auto-Create | Priority | Assignment Group |
|-------------|------------|----------|-----------------|
| CRITICAL | Yes | P1 | Regional Network Ops + On-Call |
| HIGH | Yes | P2 | Regional Network Ops |
| MEDIUM | No (manual) | P3 | Regional Network Ops |
| LOW | No | N/A | N/A |

## Field Tech Dispatch Rules

| Condition | Action |
|-----------|--------|
| CRITICAL + power outage > 1 hour | Pre-stage nearest field tech |
| CRITICAL + no backup ISP | Dispatch with portable hotspot |
| HIGH + equipment degradation | Schedule next-business-day visit |
| Any + UPS < 20% | Immediate dispatch with portable generator |

## Regional Team Mapping

| Region | Network Ops Team | Coverage Hours |
|--------|-----------------|---------------|
| Charlotte metro | charlotte-netops | 24/7 |
| Atlanta metro | atlanta-netops | 24/7 |
| Raleigh-Durham | triangle-netops | 6AM-10PM ET |
| Richmond | richmond-netops | 6AM-10PM ET |

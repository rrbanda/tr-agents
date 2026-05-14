---
name: f5-dns-validator
description: Validates DNS/IP assignments from Infoblox against environment-specific naming conventions, subnet rules, and historical patterns. Flags mismatches before F5 VIP configuration to prevent multi-cycle corrections.
compatibility: Requires access to Infoblox DNS, subnet database, and ServiceNow request details.
metadata:
  author: network-ops
  version: "1.0"
  tags: dns, validation, f5, infoblox, naming-conventions
allowed-tools: run_skill_script
---

# F5 DNS/IP Validation Instructions

When asked to validate a DNS/IP assignment for an F5 VIP request, follow this methodology:

## Step 1: Get the Request Context

Use `get_servicenow_request` to retrieve the provisioning request. Identify:
- Target environment (production, staging, development)
- Application name
- VIP name and pool configuration
- Requested protocol and port

## Step 2: Get the DNS Assignment

Use `get_dns_assignment` to retrieve the IPs and hostnames assigned by the DNS team. Note:
- Assigned hostname
- Assigned IP
- Subnet and VLAN
- Which DNS server made the assignment

## Step 3: Get Naming Conventions

Use `get_naming_conventions` with the target environment to get expected patterns:
- Hostname format (e.g. {app}.prod.internal.bank.com)
- Subnet prefix (e.g. 10.120.x.x for production)
- VLAN range (e.g. VLAN-120 through VLAN-122)
- IP range

## Step 4: Run Validation Script

Use `run_skill_script` to execute `scripts/validate_naming.py` with the collected data. The script performs deterministic checks:
- Hostname matches environment suffix (.prod. vs .stg. vs .dev.)
- IP is in the correct subnet prefix for the environment
- VLAN is in the expected range
- No conflicting environment indicators in the hostname
- IP is a valid IPv4 address

## Step 5: Check Subnet Details

Use `get_subnet_info` to verify the assigned IP's subnet:
- Confirm the subnet's labeled environment matches the request
- Check available IP count (flag if near exhaustion)
- Verify the subnet's purpose matches VIP usage

## Step 6: Check Historical Patterns

Use `get_historical_assignments` to look for similar past assignments:
- Have IPs in this range been assigned correctly before?
- Are there past validation failures with similar patterns?
- Is this a known DNS team error pattern?

## Step 7: Present Validation Results

Return findings in this format:
```json
{
  "request_id": "...",
  "overall_result": "PASS or FAIL",
  "findings": [
    {"rule": "rule_name", "status": "PASS/FAIL", "detail": "..."}
  ],
  "historical_context": "Similar assignment succeeded/failed in past",
  "recommendation": "Proceed with F5 config / Return to DNS team for correction",
  "evidence_summary": "One-paragraph summary for the approval gate"
}
```

## Step 8: Trigger Provisioning Workflow or Return to DNS Team

If validation **PASSES**:
- Use `trigger_workflow` with workflow_id `f5-vip-provisioning`
- Pass: requestId, environment, vipName, assignedIp, poolMembers, and your validationEvidence
- The RHDH Orchestrator workflow handles: F5 API configuration, connectivity checks, evidence submission to ServiceNow, and approval routing to the F5 network team
- Use `get_workflow_status` to confirm the provisioning is progressing
- You do NOT configure F5 directly -- the workflow handles automation

If validation **FAILS**:
- Do NOT trigger the workflow
- Clearly explain which rules were violated and what the correct values should be
- Reference the naming conventions document
- The request should go back to the DNS team for correction

#!/usr/bin/env python3
"""DNS/IP naming convention validator.

Deterministic validation of assigned IPs and hostnames against
environment-specific naming rules. Called by the agent via
run_skill_script for precise, non-hallucinated validation.

Input: JSON on stdin with keys: hostname, ip, environment, subnet, vlan, conventions
Output: JSON on stdout with validation results (pass/fail per rule)
"""

import json
import re
import sys


def validate(data: dict) -> dict:
    hostname = data.get("hostname", "")
    ip = data.get("ip", "")
    env = data.get("environment", "")
    subnet = data.get("subnet", "")
    vlan = data.get("vlan", "")
    conventions = data.get("conventions", {})

    findings: list[dict] = []
    passed = True

    # Rule 1: Hostname matches environment suffix
    expected_pattern = conventions.get("hostname_pattern", "")
    if env == "production" and ".prod." not in hostname:
        findings.append({
            "rule": "hostname_environment_suffix",
            "status": "FAIL",
            "detail": f"Hostname '{hostname}' missing '.prod.' for production environment",
        })
        passed = False
    elif env == "staging" and ".stg." not in hostname:
        findings.append({
            "rule": "hostname_environment_suffix",
            "status": "FAIL",
            "detail": f"Hostname '{hostname}' missing '.stg.' for staging environment",
        })
        passed = False
    else:
        findings.append({
            "rule": "hostname_environment_suffix",
            "status": "PASS",
            "detail": f"Hostname '{hostname}' matches {env} naming convention",
        })

    # Rule 2: IP in correct subnet prefix for environment
    expected_prefix = conventions.get("subnet_prefix", "")
    if expected_prefix and not ip.startswith(expected_prefix):
        findings.append({
            "rule": "ip_subnet_prefix",
            "status": "FAIL",
            "detail": (
                f"IP '{ip}' starts with '{ip.rsplit('.', 2)[0]}.' "
                f"but {env} expects prefix '{expected_prefix}'"
            ),
        })
        passed = False
    else:
        findings.append({
            "rule": "ip_subnet_prefix",
            "status": "PASS",
            "detail": f"IP '{ip}' matches {env} subnet prefix '{expected_prefix}'",
        })

    # Rule 3: VLAN in expected range
    expected_vlans = conventions.get("vlan_range", [])
    if expected_vlans and vlan and vlan not in expected_vlans:
        findings.append({
            "rule": "vlan_range",
            "status": "FAIL",
            "detail": f"VLAN '{vlan}' not in expected range {expected_vlans} for {env}",
        })
        passed = False
    elif vlan:
        findings.append({
            "rule": "vlan_range",
            "status": "PASS",
            "detail": f"VLAN '{vlan}' is in expected range for {env}",
        })

    # Rule 4: Hostname doesn't contain conflicting environment indicators
    env_indicators = {"prod": "production", "stg": "staging", "dev": "development"}
    for indicator, indicator_env in env_indicators.items():
        if indicator in hostname.lower() and indicator_env != env:
            findings.append({
                "rule": "hostname_conflicting_indicator",
                "status": "FAIL",
                "detail": (
                    f"Hostname '{hostname}' contains '{indicator}' suggesting "
                    f"{indicator_env}, but request is for {env}"
                ),
            })
            passed = False

    # Rule 5: IP is a valid IPv4
    octets = ip.split(".")
    if len(octets) != 4 or not all(o.isdigit() and 0 <= int(o) <= 255 for o in octets):
        findings.append({
            "rule": "valid_ipv4",
            "status": "FAIL",
            "detail": f"'{ip}' is not a valid IPv4 address",
        })
        passed = False
    else:
        findings.append({
            "rule": "valid_ipv4",
            "status": "PASS",
            "detail": f"'{ip}' is a valid IPv4 address",
        })

    return {
        "overall": "PASS" if passed else "FAIL",
        "findings_count": len(findings),
        "pass_count": sum(1 for f in findings if f["status"] == "PASS"),
        "fail_count": sum(1 for f in findings if f["status"] == "FAIL"),
        "findings": findings,
    }


if __name__ == "__main__":
    input_data = json.load(sys.stdin)
    output = validate(input_data)
    json.dump(output, sys.stdout, indent=2)

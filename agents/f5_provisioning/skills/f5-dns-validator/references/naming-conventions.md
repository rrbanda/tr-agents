# DNS Naming Conventions by Environment

## Production

| Field | Convention | Example |
|-------|-----------|---------|
| Hostname | `{app}.prod.internal.bank.com` | `onlinebanking.prod.internal.bank.com` |
| Subnet prefix | `10.120.` | `10.120.100.25` |
| VIP subnet | `10.120.100.0/24` or `10.120.101.0/24` | |
| VLAN | `VLAN-120` through `VLAN-122` | |
| DNS suffix | `.prod.internal.bank.com` | |

## Staging

| Field | Convention | Example |
|-------|-----------|---------|
| Hostname | `{app}.stg.internal.bank.com` | `mobilegw.stg.internal.bank.com` |
| Subnet prefix | `10.130.` | `10.130.20.10` |
| VIP subnet | `10.130.20.0/24` or `10.130.21.0/24` | |
| VLAN | `VLAN-130` or `VLAN-131` | |
| DNS suffix | `.stg.internal.bank.com` | |

## Development

| Field | Convention | Example |
|-------|-----------|---------|
| Hostname | `{app}.dev.internal.bank.com` | `payments.dev.internal.bank.com` |
| Subnet prefix | `10.140.` | `10.140.10.5` |
| VIP subnet | `10.140.10.0/24` | |
| VLAN | `VLAN-140` | |
| DNS suffix | `.dev.internal.bank.com` | |

## Common DNS Team Errors

1. **Environment mismatch**: Staging IP assigned to production request (10.130.x.x instead of 10.120.x.x)
2. **Hostname suffix wrong**: Using `.prod.` suffix for staging hostnames
3. **Conflicting indicators**: Hostname contains "stg" but assigned to production environment
4. **Wrong VLAN**: VLAN from a different environment range

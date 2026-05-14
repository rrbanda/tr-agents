# Known Failure Modes

## Weather-Related

### Severe Thunderstorm
- **Impact**: Power outages from downed lines, ISP degradation from fiber/equipment damage
- **Cascade timing**: Power loss within 0-30 min, ISP degradation within 30-90 min
- **Duration**: Typically 2-6 hours, can extend to 12+ for major storms
- **Branches most affected**: Those in flood-prone areas or near above-ground power lines

### Hurricane / Tropical Storm
- **Impact**: Extended power outages, widespread ISP failure, potential facility damage
- **Cascade timing**: Progressive degradation over 6-12 hours
- **Duration**: 12-72+ hours
- **Mitigation**: Generator pre-deployment, satellite backup activation

### Ice Storm
- **Impact**: Power line breakage, road access issues for field techs
- **Cascade timing**: Gradual accumulation, sudden failure
- **Duration**: 8-48 hours
- **Special consideration**: ATM sites without backup power go offline quickly

## Infrastructure-Related

### ISP Fiber Cut
- **Impact**: Total loss for all sites on that circuit
- **Cause**: Construction, vehicle accident, vandalism
- **Duration**: 4-8 hours for fiber repair
- **Mitigation**: Dual-ISP sites fail over automatically. Single-ISP sites need manual intervention.

### Power Grid Failure
- **Impact**: UPS provides 20-90 minutes, then full outage
- **Cause**: Substation failure, grid overload, transformer damage
- **Duration**: 2-24 hours depending on cause
- **Mitigation**: Generator deployment for extended outages

### Equipment Failure
- **Impact**: Site-specific outage
- **Indicators**: Rising CPU/temp, increasing port errors, UPS battery degradation
- **Duration**: 2-8 hours for equipment replacement
- **Mitigation**: Proactive replacement when indicators show degradation trend

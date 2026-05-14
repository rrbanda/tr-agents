# Network Operations Agents

Two ADK agents for network operations automation, orchestrated by RHDH Orchestrator with tools accessed through MCP Gateway.

## Agents

### Branch Network Monitor (`agents/branch_monitor/`)
Proactively monitors branch and ATM network health by correlating weather, power, ISP, and equipment data. Uses **live NWS Weather API** and **live Duke Energy outage API** alongside mock data for ISP and equipment monitoring.

### F5 VIP Provisioning (`agents/f5_provisioning/`)
Validates DNS/IP assignments against naming conventions before F5 configuration, using an **executable validation script** for deterministic rule checking.

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env

# Run Branch Monitor
PYTHONPATH=. adk web --host 0.0.0.0 --port 8001 --session_service_uri memory:// agents

# Run tests
pytest tests/ -v
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture document with diagrams.

```
agents/
├── branch_monitor/           # Use Case 2: Proactive monitoring
│   ├── agent.py
│   ├── server.py
│   └── skills/branch-network-monitor/
│       ├── SKILL.md
│       ├── scripts/correlate_threats.py    # Executable scoring
│       └── references/
├── f5_provisioning/          # Use Case 1: VIP provisioning
│   ├── agent.py
│   └── skills/f5-dns-validator/
│       ├── SKILL.md
│       ├── scripts/validate_naming.py     # Executable validation
│       └── references/
shared/
├── branch_monitor_tools.py   # 8 tools (2 live APIs + mock)
├── f5_tools.py               # 8 tools (mock)
└── model_config.py
workflows/
├── f5-vip-provisioning.sw.yaml       # SonataFlow workflow
└── branch-outage-response.sw.yaml    # SonataFlow workflow
mcp-servers/
├── weather-mcp-server.yaml           # NWS API (live)
├── power-outage-mcp-server.yaml      # Duke Energy (live)
├── infoblox-mcp-server.yaml
├── f5-mcp-server.yaml
├── servicenow-mcp-server.yaml
└── network-monitoring-mcp-server.yaml
```

## License

Apache 2.0

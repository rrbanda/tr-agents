# MCP Server Interfaces

Each MCP server wraps an external system and exposes it as tools via the
Model Context Protocol. Both the RHDH Orchestrator workflows and the
ADK agents consume these through the Kagenti MCP Gateway.

## Server Inventory

| MCP Server | Backend System | Used By | Auth |
|-----------|---------------|---------|------|
| `weather-mcp-server` | NWS API (api.weather.gov) | Branch Monitor Agent | None (public) |
| `power-outage-mcp-server` | Duke Energy ArcGIS API | Branch Monitor Agent | None (public) |
| `isp-status-mcp-server` | Downdetector / StatusPage APIs | Branch Monitor Agent | API key (paid) |
| `network-monitoring-mcp-server` | SolarWinds / SNMP | Branch Monitor Agent | Internal API key |
| `branch-inventory-mcp-server` | Internal database | Branch Monitor Agent | Internal |
| `infoblox-mcp-server` | Infoblox WAPI | F5 Provisioning Workflow + Agent | Internal API key |
| `f5-mcp-server` | F5 BIG-IP iControl REST | F5 Provisioning Workflow | Internal API key |
| `servicenow-mcp-server` | ServiceNow REST API | Both workflows | OAuth2 |
| `connectivity-mcp-server` | Internal ping/health checks | F5 Provisioning Workflow | Internal |
| `notifications-mcp-server` | Teams / PagerDuty / SMS | Response Workflow | API keys |
| `dispatch-mcp-server` | Field tech scheduling system | Response Workflow | Internal |

# Network Operations Agents

AI agents for network operations automation on Red Hat OpenShift, using the **Agent + Orchestrator** architectural pattern to solve two real enterprise problems. Tools are accessed via direct Python functions and REST APIs, with an MCP server deployed for ServiceNow integration.

---

## The Problem

### Use Case 1: F5 VIP Provisioning (6 weeks to minutes)

Today, when the OpenShift platform team needs an F5 VIP, they open a ServiceNow request. The network engineering team reviews it, opens another ticket to the Cisco CMS team, and the DNS team assigns IPs and hostnames. **Most of the time, the DNS assignments are wrong** -- wrong subnet for the environment, wrong hostname suffix, wrong VLAN. The CMS team doesn't verify the assignments and implements the change as-is. The configuration fails, and it takes **multiple fix cycles over 6 weeks to months** to get a single F5 VIP configured correctly.

### Use Case 2: Branch/ATM Network Monitoring (reactive to proactive)

The network team managing branch and ATM networks is **reactive, not proactive**. When a power outage, ISP failure, or equipment malfunction affects a branch, the team finds out late. Sometimes staff drives all the way to the branch only to discover the issue could have been predicted from publicly available data -- weather warnings, utility outage feeds, ISP status reports.

---

## The Solution: Agent + Orchestrator

This project implements the **correct architectural separation of concerns** for enterprise AI automation. It uses three layers, each doing what it does best:

```
Layer            Responsibility                         Technology
─────────────    ─────────────────────────────────────   ──────────────────────
Agent            Understand, reason, decide              Google ADK + Skills
Orchestrator     Execute process, track state, audit     SonataFlow + RHDH
Tools/APIs       Discrete actions and integrations       Python tools, REST APIs, MCP (ServiceNow)
```

### Why Not Just Let the Agent Do Everything?

A common mistake is having the AI agent coordinate the entire process through sequential tool calls (Design 1). This creates five structural problems:

| Problem | What Goes Wrong | How We Solve It |
|---------|----------------|-----------------|
| **No durable state** | Chat session ends, process is lost | SonataFlow persists every workflow instance in Data-Index |
| **No wait semantics** | Approval takes days, agent can't park | SonataFlow supports event-driven wait states natively |
| **No determinism** | LLM may skip steps or reorder them | Workflow YAML defines exact sequence, executed identically every time |
| **No error recovery** | Two identical failures, two different recoveries | SonataFlow has explicit retry policies and compensation |
| **Token waste** | Every intermediate API response flows through the LLM | Agent makes 1 call to trigger, 1 call to check status |

### How It Works in Our Implementation

```
Developer/Operator
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  AGENT LAYER (Google ADK)                                   │
│                                                             │
│  Understands the request                                    │
│  Loads skill (agentskills.io)                               │
│  Gathers data from multiple sources                         │
│  Runs deterministic validation scripts                      │
│  Decides: trigger workflow or block with explanation         │
│                                                             │
│  trigger_workflow("branch-outage-response", {...})           │
│       │                                                     │
└───────┼─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR LAYER (SonataFlow / RHDH)                     │
│                                                             │
│  Receives workflow trigger with parameters                  │
│  Executes declared states in exact order:                   │
│    1. Send Teams notification                               │
│    2. Send SMS to branch manager                            │
│    3. Create ServiceNow P1 incident (REAL)                  │
│    4. Produce structured output                             │
│  Data-Index tracks every node (18 nodes per execution)      │
│  Instance survives restarts, queryable via GraphQL          │
│                                                             │
└───────┼─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  TOOL LAYER (Python tools + REST APIs)                      │
│                                                             │
│  Agent tools (shared/*.py):                                 │
│    NWS Weather API ← real county-level weather alerts       │
│    Duke Energy API ← real ZIP-level power outage data       │
│    ISP/Equipment   ← mock (swap for real monitoring APIs)   │
│    Infoblox DNS    ← mock (swap for real Infoblox API)      │
│                                                             │
│  Workflow REST clients (SonataFlow → external services):    │
│    ServiceNow API  ← creates real incidents (INC0010001+)   │
│    F5 iControl     ← VIP configuration (mock for POC)      │
│    Teams/SMS       ← notifications (mock for POC)           │
│                                                             │
│  ServiceNow MCP Server (deployed, 93 tools, not yet wired  │
│  into agent -- available for future ad-hoc queries)         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

The agent handles the two bookend interactions -- intake and status inquiry. The Orchestrator owns everything in between. MCP tools and APIs are the verbs that both layers use to perform actual work.

---

## What's Deployed on OpenShift

| Service | Namespace | Purpose | Status |
|---------|-----------|---------|--------|
| branch-monitor (ADK agent) | tr-agents | Agent + ADK Web UI + A2A protocol | Running |
| branch-outage-response | sonataflow-infra | SonataFlow workflow (Quarkus/Kogito) | Running |
| f5-vip-provisioning | sonataflow-infra | SonataFlow workflow (Quarkus/Kogito) | Running |
| Data-Index Service | sonataflow-infra | GraphQL workflow instance tracking | Running |
| Jobs Service | sonataflow-infra | Workflow timer/scheduling | Running |
| PostgreSQL | sonataflow-infra | Data-Index persistence | Running |
| Mock Backends + ServiceNow Proxy | sonataflow-infra | Teams/SMS mock + real ServiceNow proxy | Running |
| ServiceNow MCP Server (93 tools) | sonataflow-infra | Real ServiceNow integration via MCP | Running |
| RHDH (Backstage) | rhdh | Orchestrator UI + plugins | Running |
| SonataFlow Operator | openshift-operators | Workflow lifecycle management | Running |

---

## Demo Guide

### Demo Moment 1: F5 FAIL -- Agent Catches Bad DNS Assignment

**TELL:** "When the DNS team assigns IPs and hostnames for an F5 VIP request, they frequently get them wrong -- production IPs assigned to staging, wrong hostname suffixes, wrong VLANs. Today, nobody catches this until the Cisco CMS team implements it and it fails. That leads to multiple fix cycles over 6 weeks."

**SHOW:**

1. Open ADK Web UI: `https://branch-monitor-tr-agents.apps.<cluster>/dev-ui/`
2. Select **`f5_provisioning`** from the agent dropdown
3. Type: **`Validate the DNS assignment for ServiceNow request REQ-2025-0903`**
4. Watch the agent:
   - Load the `f5-dns-validator` skill
   - Retrieve the ServiceNow request (staging environment, mobile-gateway app)
   - Retrieve the DNS assignment (hostname: `mobilegw-stg.prod.internal.bank.com`)
   - Retrieve staging naming conventions (expects `.stg.` suffix, `10.130.*` subnet)
   - Execute `validate_naming.py` -- deterministic script, not LLM guessing
   - Find **4 validation failures**:
     - Hostname has `.prod.` suffix but request is for staging
     - IP `10.120.100.30` is in production subnet, staging expects `10.130.*`
     - VLAN-120 is production, staging expects VLAN-130/131
     - Hostname contains `prod` but request is for staging environment
   - Reference historical failures (REQ-2025-0698 had the same subnet mismatch)
   - **Block the workflow** -- do NOT trigger F5 provisioning

**TELL:** "The agent caught 4 errors in this DNS assignment before it reached F5. Without this gate, the CMS team would have implemented the wrong configuration, it would have failed, and the team would have spent weeks in fix cycles. The agent is the validation gate that prevents the core problem."

**Key concept -- why this needs AI, not just rules:**
- The validation script (`validate_naming.py`) handles the deterministic checks -- this IS pure automation
- But the agent adds: historical pattern matching ("this same error happened on REQ-2025-0698"), natural language evidence synthesis, and the decision to block or proceed
- The agent loads its methodology from an **agentskills.io skill** -- a portable, reusable capability package

---

### Demo Moment 2: Branch CRITICAL -- Proactive Detection with Real ServiceNow

**TELL:** "Today the network team is reactive. When a power outage or ISP failure hits a branch, staff sometimes drives 45 minutes only to discover the power was out. That information was publicly available hours earlier from the utility company and the weather service."

**SHOW:**

1. Switch to **`branch_monitor`** in the agent dropdown
2. Type: **`Assume severe weather warning for Charlotte NC. Check branch BR-4471 and assess the threat. If CRITICAL, trigger the response workflow.`**
3. Watch the agent:
   - Load the `branch-network-monitor` skill
   - Call `get_branch_inventory("charlotte")` -- finds BR-4471 (South Tryon Street) + ATM-28202-A
   - Call `get_weather_alerts("NC", "Mecklenburg")` -- **REAL NWS API** (live data)
   - Call `get_power_outage_status("28202")` -- **REAL Duke Energy API** (live data)
   - Call `get_isp_status` -- AT&T Business degraded (145ms latency, 4.2% packet loss)
   - Call `get_equipment_health("BR-4471")` -- primary link degraded (210ms, 6.1% packet loss)
   - Execute `correlate_threats.py` -- weighted threat scoring (weather 40, power 30, ISP 20, equipment 10)
   - Assess threat as **CRITICAL**
   - Call `trigger_workflow("branch-outage-response")` -- hands off to the Orchestrator
   - SonataFlow executes the response workflow:
     - Send Teams notification to charlotte-netops
     - Send SMS to branch manager
     - Create **REAL ServiceNow P1 incident** in the PDI
   - Call `get_workflow_status` -- Data-Index confirms COMPLETED, 18 nodes executed

4. Open your ServiceNow PDI instance -- show the real incident created by the workflow

**TELL:** "A P1 incident was created in ServiceNow, the network team was alerted, the branch manager was notified -- all in seconds, all before anyone at the branch noticed the outage. The agent correlated weather, power, ISP, and equipment data from multiple sources that no single system has together. That's why this needs AI -- the correlation and judgment across disparate data sources."

**Key concept -- Agent vs Orchestrator separation:**
- The **agent** decided the threat was CRITICAL (AI reasoning across 4 data sources)
- The **Orchestrator** executed the response (Teams + SMS + ServiceNow -- deterministic, auditable, durable)
- If the agent had done the response directly, there would be no audit trail, no retry on failure, no persistent state
- The Data-Index tracked all 18 workflow nodes -- that's the evidence trail the customer asked for

---

## How It Works: Step by Step

### Use Case 1: F5 VIP Provisioning

```
1. ServiceNow request exists (REQ-2025-0903)
   └── Platform team opened it, DNS team assigned IPs

2. Agent loads f5-dns-validator skill
   └── SKILL.md defines the methodology
   └── scripts/validate_naming.py provides deterministic validation
   └── references/naming-conventions.md documents the rules

3. Agent gathers data
   ├── get_servicenow_request("REQ-2025-0903") → environment, VIP config
   ├── get_dns_assignment("REQ-2025-0903")     → hostname, IP, VLAN
   └── get_naming_conventions("staging")        → expected patterns

4. Agent runs validation script
   └── run_skill_script("validate_naming.py", data)
   └── Returns: PASS or FAIL with specific findings per rule

5. Decision gate
   ├── FAIL → Agent explains errors, references history, blocks workflow
   └── PASS → Agent calls trigger_workflow("f5-vip-provisioning")

6. SonataFlow workflow executes (only if PASS)
   ├── State 1: Configure F5 VIP via iControl REST
   ├── State 2: Run connectivity checks
   ├── State 3: Update ServiceNow with evidence (REAL)
   └── State 4: Request F5 team approval

7. RHDH Orchestrator tracks everything
   └── Data-Index indexes all nodes via GraphQL
   └── Backstage UI shows workflow status
```

### Use Case 2: Branch/ATM Monitoring

```
1. Agent loads branch-network-monitor skill
   └── SKILL.md defines monitoring methodology
   └── scripts/correlate_threats.py computes weighted threat scores
   └── references/threat-assessment.md, escalation-matrix.md

2. Agent gathers data from 4 sources
   ├── get_weather_alerts("NC", "Mecklenburg")     → REAL NWS API
   ├── get_power_outage_status("28202")             → REAL Duke Energy API
   ├── get_isp_status("att_business", "charlotte")  → mock (AT&T degraded)
   └── get_equipment_health("BR-4471")              → mock (primary link degraded)

3. Agent runs threat scoring script
   └── correlate_threats.py: weather(40) + power(30) + ISP(20) + equipment(10)
   └── Returns: threat level (CRITICAL/HIGH/MEDIUM/LOW) + score

4. Response routing
   ├── CRITICAL/HIGH → trigger_workflow("branch-outage-response")
   │   └── SonataFlow: Teams alert → SMS → ServiceNow P1 (REAL)
   ├── MEDIUM → send_alert directly (no workflow needed)
   └── LOW → note and monitor

5. Status verification
   └── get_workflow_status(instance_id) → Data-Index GraphQL
   └── Returns: COMPLETED, 18 nodes, incident number
```

---

## Key Concepts

### agentskills.io

An open specification for packaging agent capabilities as portable skills. Each skill contains:
- `SKILL.md` -- methodology definition (what the agent should do step by step)
- `scripts/` -- executable programs for deterministic computation (not LLM inference)
- `references/` -- context documents the agent can load (naming conventions, threat assessment criteria, escalation matrices)
- `evals/` -- evaluation data for testing skill quality

Skills are loaded by the ADK agent at startup and provide tools like `load_skill`, `run_skill_script`, and `load_skill_resource`.

### Executable Scripts (Deterministic, Not Hallucinated)

Critical validation and scoring logic runs in Python scripts, NOT in the LLM:
- `validate_naming.py` -- checks 5 rules (hostname suffix, IP subnet, VLAN range, conflicting indicators, valid IPv4). Returns exact PASS/FAIL per rule.
- `correlate_threats.py` -- computes weighted threat scores from 4 data sources. Returns exact numeric score and threat level.

This ensures consistency. The LLM interprets and explains the results, but the computation is deterministic.

### SonataFlow (RHDH Orchestrator)

A cloud-native workflow engine based on the CNCF Serverless Workflow specification, running on Quarkus/Kogito:
- **Declarative**: Workflows defined in YAML, executed identically every time
- **Durable**: Every instance persisted in Data-Index with PostgreSQL
- **Observable**: GraphQL API for querying instance state, nodes, variables
- **Integrated**: RHDH Orchestrator plugin provides Backstage UI and REST API

### A2A (Agent-to-Agent Protocol)

Both agents expose A2A endpoints for agent interoperability. This means other agents (or MCP clients) can discover and call them programmatically using the JSON-RPC-based A2A protocol.

---

## What's Real vs What's Mock

| Component | Status | Detail |
|-----------|--------|--------|
| NWS Weather API | **REAL** | Live api.weather.gov, county-level alerts |
| Duke Energy Power Outages | **REAL** | Live ArcGIS API, ZIP-level outage data |
| ServiceNow Incidents | **REAL** | Creates real incidents in ServiceNow PDI (INC0010001+ confirmed) |
| SonataFlow Workflows | **REAL** | Quarkus/Kogito on OpenShift, 18 nodes per execution |
| Data-Index / Orchestrator | **REAL** | PostgreSQL-backed GraphQL, tracks all instances |
| ServiceNow MCP Server | **REAL** | 93 tools deployed, connected to PDI |
| RHDH Orchestrator Plugin | **REAL** | Backend loaded, discovering workflows |
| Agent Skills + Scripts | **REAL** | agentskills.io format, executable validation |
| ISP Status | Mock | Simulated AT&T/Spectrum data. Needs: ThousandEyes or BGP monitoring |
| Equipment Health | Mock | Simulated SNMP data. Needs: Zabbix, SolarWinds, or PRTG |
| Branch Inventory | Mock | Hardcoded Charlotte branches. Needs: CMDB or ServiceNow CMDB query |
| F5 iControl REST | Mock | Workflow calls mock backend. Needs: real F5 BIG-IP IP address |
| Infoblox DNS | Mock | Hardcoded assignments. Needs: real Infoblox API |
| Teams Notifications | Mock | Logs but doesn't send. Needs: Teams webhook URL |
| SMS Alerts | Mock | Logs but doesn't send. Needs: Twilio or SMS gateway |

**To make any mock component real:** swap the tool function or update `application.properties` with the real endpoint URL. The agent, skills, scoring, workflows, and orchestrator are all production-ready.

---

## Setup and Deployment

### Prerequisites

- OpenShift 4.18+ with cluster-admin access
- `oc` CLI installed and authenticated
- Python 3.12+ (for local development)
- ServiceNow PDI (free at [developer.servicenow.com](https://developer.servicenow.com))

### Configuration

The project uses two config files:

- **`config.yaml`** -- LLM endpoint and agent metadata (non-secret)
- **`.env`** -- secrets and environment-specific overrides

`config.yaml` supports environment variable substitution:
```yaml
model:
  agent:
    id: "${LLM_MODEL_ID:-openai/gemini/models/gemini-2.5-flash}"
    api_base: "${LLM_API_BASE:-https://your-llamastack-url/v1}"
    api_key: "${LLAMASTACK_API_KEY:-not-needed}"
```

### Local Development

```bash
git clone https://github.com/rrbanda/tr-agents.git
cd tr-agents
pip install -e .
cp .env.example .env
# Edit .env with your LLM endpoint and ServiceNow credentials

# Run both agents with ADK Web UI
PYTHONPATH=. adk web --host 0.0.0.0 --port 8000 --a2a --session_service_uri memory:// agents

# Run tests
pytest tests/ -v
```

### OpenShift Deployment

**Prerequisites:** SonataFlow Operator installed, SonataFlowPlatform CR created in `sonataflow-infra` namespace (provides Data-Index, Jobs Service, PostgreSQL).

```bash
# 1. Create namespaces
oc new-project tr-agents
oc new-project sonataflow-infra

# 2. Build and deploy agent
oc new-build --binary --name=branch-monitor --strategy=docker -n tr-agents
oc start-build branch-monitor --from-dir=. --follow -n tr-agents
oc new-app branch-monitor --name=branch-monitor -n tr-agents
oc expose svc/branch-monitor -n tr-agents

# 3. Build SonataFlow workflows
# The Dockerfile.workflow uses the SonataFlow builder image (NOT offline mode)
cd workflows/branch-outage-response
oc new-build --binary --name=branch-outage-response-quarkus --strategy=docker -n sonataflow-infra
oc start-build branch-outage-response-quarkus --from-dir=. --follow -n sonataflow-infra
oc new-app branch-outage-response-quarkus --name=branch-outage-response -n sonataflow-infra
# Repeat for f5-vip-provisioning

# 4. Deploy mock backends (Teams/SMS mock + ServiceNow proxy)
cd mock-backends
oc new-build --binary --name=mock-workflow-backends --strategy=docker -n sonataflow-infra
oc start-build mock-workflow-backends --from-dir=. --follow -n sonataflow-infra
oc new-app mock-workflow-backends --name=mock-workflow-backends -n sonataflow-infra

# 5. Configure ServiceNow credentials (no secrets in code)
oc set env deploy/mock-workflow-backends \
  SERVICENOW_URL=https://devXXXXXX.service-now.com \
  SERVICENOW_USERNAME=admin \
  SERVICENOW_PASSWORD=<your-password> \
  -n sonataflow-infra

# 6. (Optional) Deploy ServiceNow MCP Server
# See https://github.com/echelon-ai-labs/servicenow-mcp
```

**Note on SonataFlow Operator:** The community operator v10.1.0 has a broken `kube-rbac-proxy` sidecar image (`gcr.io/kubebuilder/kube-rbac-proxy:v0.13.1`). Fix by patching the CSV: `oc patch csv sonataflow-operator.v10.1.0 -n openshift-operators --type='json' -p='[{"op":"replace","path":"/spec/install/spec/deployments/0/spec/template/spec/containers/1/image","value":"quay.io/brancz/kube-rbac-proxy:v0.18.1"}]'`

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_API_BASE` | LLM endpoint URL | LlamaStack on OpenShift |
| `LLM_MODEL_ID` | Model identifier | `openai/gemini/models/gemini-2.5-flash` |
| `SERVICENOW_URL` | ServiceNow PDI URL | (none) |
| `SERVICENOW_USERNAME` | ServiceNow admin user | `admin` |
| `SERVICENOW_PASSWORD` | ServiceNow password | (none) |
| `SONATAFLOW_NAMESPACE` | Workflow namespace | `sonataflow-infra` |

---

## Project Structure

```
agents/
├── branch_monitor/                    # Use Case 2: Proactive monitoring
│   ├── agent.py                       # ADK Agent definition (12 tools)
│   ├── server.py                      # A2A server entrypoint
│   └── skills/branch-network-monitor/
│       ├── SKILL.md                   # Monitoring methodology
│       ├── scripts/correlate_threats.py    # Deterministic threat scoring
│       └── references/
│           ├── threat-assessment.md
│           ├── escalation-matrix.md
│           └── known-failure-modes.md
├── f5_provisioning/                   # Use Case 1: VIP provisioning
│   ├── agent.py                       # ADK Agent definition (12 tools)
│   └── skills/f5-dns-validator/
│       ├── SKILL.md                   # Validation methodology
│       ├── scripts/validate_naming.py     # Deterministic DNS validation
│       └── references/
│           └── naming-conventions.md
shared/
├── branch_monitor_tools.py            # 8 tools (2 live APIs + 6 mock)
├── f5_tools.py                        # 8 tools (all mock)
├── orchestrator_tools.py              # SonataFlow REST + Data-Index GraphQL
└── model_config.py                    # LLM configuration loader
workflows/
├── branch-outage-response/            # SonataFlow workflow (Quarkus project)
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/main/resources/
│       ├── branch-outage-response.sw.yaml    # Workflow definition
│       ├── application.properties
│       ├── specs/                     # OpenAPI specs for external services
│       └── schemas/                   # JSON schemas for input/output
├── f5-vip-provisioning/               # SonataFlow workflow (Quarkus project)
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/main/resources/
│       ├── f5-vip-provisioning.sw.yaml
│       ├── application.properties
│       ├── specs/
│       └── schemas/
└── Dockerfile.workflow                # Shared Dockerfile for workflow builds
mock-backends/
├── app.py                             # Teams/SMS mock + ServiceNow proxy
└── Dockerfile
tests/
├── test_branch_monitor.py
└── test_f5_provisioning.py
```

---

## License

Apache 2.0

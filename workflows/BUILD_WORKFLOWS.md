# Building and Deploying Workflows

Follows the [RHDH Orchestrator demo](https://github.com/rhdhorchestrator/orchestrator-demo) pattern.

## Prerequisites

- `kn-workflow` v1.36+ installed
- Podman or Docker
- Access to a container registry (quay.io, GHCR, or internal)
- RHDH with Orchestrator plugin installed on OpenShift

## Build a Workflow

```bash
# From the workflow directory (e.g. workflows/f5-vip-provisioning)
cd workflows/f5-vip-provisioning

# Generate K8s manifests
kn-workflow gen-manifest \
  -c=manifests \
  --profile=gitops \
  --image=quay.io/your-org/f5-vip-provisioning:v1 \
  --namespace=orchestrator

# Build the container image
podman build \
  -f ../../resources/workflow-builder.Dockerfile \
  --tag quay.io/your-org/f5-vip-provisioning:v1 \
  --platform linux/amd64 \
  .

# Push
podman push quay.io/your-org/f5-vip-provisioning:v1

# Deploy
kubectl apply -f manifests/ -n orchestrator
```

## Using the Workflow Builder Image

Alternatively, use the orchestrator workflow builder container:

```bash
podman run --rm --privileged \
  -v $HOME/.config/containers/auth.json:/root/.config/containers/auth.json:ro \
  -v $(pwd)/workflows/f5-vip-provisioning:/workspace \
  quay.io/orchestrator/orchestrator-workflow-builder:1.35 \
  -i quay.io/your-org/f5-vip-provisioning:v1 \
  -w /workspace \
  -m /workspace/manifests \
  --push --deploy
```

## Generated Manifests

After `kn-workflow gen-manifest`, the `manifests/` directory contains:

| File | Purpose |
|------|---------|
| `00-secret.yaml` | Secrets for API credentials |
| `01-configmap-props.yaml` | application.properties |
| `02-configmap-schemas.yaml` | JSON schemas (input/output) |
| `03-configmap-specs.yaml` | OpenAPI specs for external services |
| `04-sonataflow.yaml` | SonataFlow CR (the workflow itself) |

## How the Agent Triggers These Workflows

The agents don't run inside workflows. They call the RHDH Orchestrator REST API to trigger workflows:

```
POST /v2/workflows/{workflow_id}/instances
```

The `shared/orchestrator_tools.py` module provides:
- `trigger_workflow(workflow_id, input_data)` -- starts a workflow
- `get_workflow_status(instance_id)` -- checks progress
- `list_available_workflows()` -- shows what's available

The agent does the AI reasoning, then hands off to the workflow for deterministic automation.

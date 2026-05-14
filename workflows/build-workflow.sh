#!/usr/bin/env bash
set -euo pipefail

# Build and optionally deploy a SonataFlow workflow for RHDH Orchestrator.
# Follows the pattern from https://github.com/rhdhorchestrator/orchestrator-demo
#
# Usage:
#   ./build-workflow.sh f5-vip-provisioning quay.io/your-org/f5-vip-provisioning:v1
#   ./build-workflow.sh branch-outage-response quay.io/your-org/branch-outage-response:v1 --push --deploy
#
# Prerequisites:
#   - kn-workflow v1.36+ (https://mirror.openshift.com/pub/cgw/serverless-logic/1.36.0/)
#   - podman or docker
#   - For --deploy: kubectl/oc logged into target cluster

WORKFLOW_NAME="${1:?Usage: $0 <workflow-name> <image> [--push] [--deploy]}"
IMAGE="${2:?Usage: $0 <workflow-name> <image> [--push] [--deploy]}"
PUSH=""
DEPLOY=""
NAMESPACE="${NAMESPACE:-orchestrator}"

shift 2
while [[ $# -gt 0 ]]; do
    case "$1" in
        --push) PUSH="yes" ;;
        --deploy) DEPLOY="yes"; PUSH="yes" ;;
        --namespace=*) NAMESPACE="${1#*=}" ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKFLOW_DIR="${SCRIPT_DIR}/${WORKFLOW_NAME}"

if [[ ! -d "$WORKFLOW_DIR" ]]; then
    echo "ERROR: Workflow directory not found: $WORKFLOW_DIR"
    echo "Available workflows:"
    ls -d "${SCRIPT_DIR}"/*/src 2>/dev/null | xargs -I{} dirname {} | xargs -I{} basename {}
    exit 1
fi

echo "=== Building workflow: ${WORKFLOW_NAME} ==="
echo "Image: ${IMAGE}"
echo "Namespace: ${NAMESPACE}"

# Step 1: Generate manifests
echo ""
echo "=== Step 1: Generate K8s manifests ==="
cd "${WORKFLOW_DIR}/src/main/resources"
mkdir -p "${WORKFLOW_DIR}/manifests"

kn-workflow gen-manifest \
    -c="${WORKFLOW_DIR}/manifests" \
    --profile=gitops \
    --image="${IMAGE}" \
    --namespace="${NAMESPACE}"

echo "Manifests generated in: ${WORKFLOW_DIR}/manifests/"
ls -la "${WORKFLOW_DIR}/manifests/"

# Step 2: Build container image
echo ""
echo "=== Step 2: Build container image ==="

BUILDER_IMAGE="registry.redhat.io/openshift-serverless-1/logic-swf-builder-rhel9:1.37.1"
RUNTIME_IMAGE="registry.access.redhat.com/ubi9/openjdk-17-runtime:1.23"

# Detect container engine
if command -v docker &>/dev/null; then
    ENGINE="docker"
elif command -v podman &>/dev/null; then
    ENGINE="podman"
else
    echo "ERROR: Neither docker nor podman found"
    exit 1
fi

echo "Using container engine: ${ENGINE}"

# Use the orchestrator workflow builder if available
if ${ENGINE} image inspect quay.io/orchestrator/orchestrator-workflow-builder:1.35 &>/dev/null; then
    echo "Using orchestrator workflow builder image"
    BUILDER_ARGS=(
        --rm --privileged
        -v "${WORKFLOW_DIR}:/workspace"
        quay.io/orchestrator/orchestrator-workflow-builder:1.35
        -i "${IMAGE}"
        -w /workspace
        -m /workspace/manifests
    )
    [[ -n "$PUSH" ]] && BUILDER_ARGS+=(--push)
    [[ -n "$DEPLOY" ]] && BUILDER_ARGS+=(--deploy)
    ${ENGINE} run "${BUILDER_ARGS[@]}"
else
    echo "Building with local Dockerfile"
    ${ENGINE} build \
        -f "${SCRIPT_DIR}/../resources/workflow-builder.Dockerfile" \
        --tag "${IMAGE}" \
        --platform linux/amd64 \
        --build-arg "BUILDER_IMAGE=${BUILDER_IMAGE}" \
        --build-arg "RUNTIME_IMAGE=${RUNTIME_IMAGE}" \
        "${WORKFLOW_DIR}"

    if [[ -n "$PUSH" ]]; then
        echo ""
        echo "=== Step 3: Push image ==="
        ${ENGINE} push "${IMAGE}"
    fi

    if [[ -n "$DEPLOY" ]]; then
        echo ""
        echo "=== Step 4: Deploy manifests ==="
        kubectl apply -f "${WORKFLOW_DIR}/manifests/" -n "${NAMESPACE}"
    fi
fi

echo ""
echo "=== Done ==="
echo "Workflow: ${WORKFLOW_NAME}"
echo "Image: ${IMAGE}"
echo "Manifests: ${WORKFLOW_DIR}/manifests/"
[[ -n "$DEPLOY" ]] && echo "Deployed to namespace: ${NAMESPACE}"

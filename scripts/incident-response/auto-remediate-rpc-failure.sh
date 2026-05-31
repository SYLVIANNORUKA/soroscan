#!/bin/bash
# Auto-remediation script for RPC endpoint failures
# Triggered by Prometheus alert: RPCEndpointDown

set -e

NAMESPACE="${NAMESPACE:-soroscan}"
RPC_TIMEOUT="${RPC_TIMEOUT:-5}"

echo "[$(date)] Starting auto-remediation for RPC endpoint failure..."

# Function to test RPC endpoint health
test_rpc_endpoint() {
    local endpoint=$1
    local timeout=${2:-5}
    
    response=$(timeout "$timeout" curl -s -X POST "$endpoint" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}' \
        -w "\n%{http_code}" 2>/dev/null || echo "000")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Get current RPC URL
CURRENT_RPC=$(kubectl get configmap soroscan-config -n "$NAMESPACE" -o jsonpath='{.data.STELLAR_RPC_URL}')
echo "[$(date)] Current RPC endpoint: $CURRENT_RPC"

# Test current endpoint
echo "[$(date)] Testing current RPC endpoint..."
if test_rpc_endpoint "$CURRENT_RPC" "$RPC_TIMEOUT"; then
    echo "[$(date)] Current RPC endpoint is healthy. No action needed."
    exit 0
fi

echo "[$(date)] Current RPC endpoint is unhealthy. Attempting failover..."

# Get backup RPC URLs (comma-separated)
BACKUP_RPCS=$(kubectl get configmap soroscan-config -n "$NAMESPACE" -o jsonpath='{.data.STELLAR_RPC_BACKUP_URLS}' 2>/dev/null || echo "")

if [ -z "$BACKUP_RPCS" ]; then
    echo "[$(date)] ERROR: No backup RPC endpoints configured"
    # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"🚨 CRITICAL: Primary RPC down and no backups configured!\"}"
    exit 1
fi

# Try each backup endpoint
IFS=',' read -ra RPC_ARRAY <<< "$BACKUP_RPCS"
HEALTHY_RPC=""

for rpc in "${RPC_ARRAY[@]}"; do
    rpc=$(echo "$rpc" | xargs)  # Trim whitespace
    echo "[$(date)] Testing backup RPC: $rpc"
    
    if test_rpc_endpoint "$rpc" "$RPC_TIMEOUT"; then
        echo "[$(date)] Found healthy backup RPC: $rpc"
        HEALTHY_RPC="$rpc"
        break
    fi
done

if [ -z "$HEALTHY_RPC" ]; then
    echo "[$(date)] ERROR: No healthy RPC endpoints found"
    # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"🚨 CRITICAL: All RPC endpoints are down!\"}"
    exit 1
fi

# Update ConfigMap with new RPC endpoint
echo "[$(date)] Failing over to: $HEALTHY_RPC"
kubectl patch configmap soroscan-config -n "$NAMESPACE" --type merge -p "{\"data\":{\"STELLAR_RPC_URL\":\"$HEALTHY_RPC\"}}"

# Restart workers to pick up new config
echo "[$(date)] Restarting workers to apply new RPC endpoint..."
kubectl rollout restart deployment/soroscan-worker -n "$NAMESPACE"

# Wait for rollout
kubectl rollout status deployment/soroscan-worker -n "$NAMESPACE" --timeout=5m

# Verify workers are using new endpoint
sleep 10
echo "[$(date)] Verifying failover..."
if test_rpc_endpoint "$HEALTHY_RPC" "$RPC_TIMEOUT"; then
    echo "[$(date)] Failover successful!"
    
    # Send notification
    # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"✅ RPC failover successful: $CURRENT_RPC → $HEALTHY_RPC\"}"
    
    exit 0
else
    echo "[$(date)] ERROR: Failover verification failed"
    # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"⚠️ RPC failover completed but verification failed\"}"
    exit 1
fi

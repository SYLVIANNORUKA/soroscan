#!/bin/bash
# Auto-remediation script for event ingestion lag
# Triggered by Prometheus alert: EventIngestionLagHigh

set -e

NAMESPACE="${NAMESPACE:-soroscan}"
QUEUE_THRESHOLD="${QUEUE_THRESHOLD:-10000}"
MAX_WORKERS="${MAX_WORKERS:-20}"
SCALE_INCREMENT="${SCALE_INCREMENT:-2}"

echo "[$(date)] Starting auto-remediation for ingestion lag..."

# Function to get Celery queue depth
get_queue_depth() {
    kubectl exec -it deployment/soroscan-worker -n "$NAMESPACE" -- \
        celery -A soroscan inspect active_queues 2>/dev/null | \
        grep -oP '"length": \K\d+' | \
        awk '{sum+=$1} END {print sum}'
}

# Function to get current worker replicas
get_worker_replicas() {
    kubectl get deployment soroscan-worker -n "$NAMESPACE" \
        -o jsonpath='{.spec.replicas}'
}

# Check queue depth
QUEUE_DEPTH=$(get_queue_depth)
echo "[$(date)] Current queue depth: $QUEUE_DEPTH"

if [ "$QUEUE_DEPTH" -gt "$QUEUE_THRESHOLD" ]; then
    echo "[$(date)] Queue depth exceeds threshold ($QUEUE_THRESHOLD). Scaling workers..."
    
    CURRENT_REPLICAS=$(get_worker_replicas)
    NEW_REPLICAS=$((CURRENT_REPLICAS + SCALE_INCREMENT))
    
    if [ "$NEW_REPLICAS" -le "$MAX_WORKERS" ]; then
        echo "[$(date)] Scaling workers from $CURRENT_REPLICAS to $NEW_REPLICAS..."
        kubectl scale deployment soroscan-worker -n "$NAMESPACE" --replicas="$NEW_REPLICAS"
        
        # Wait for rollout
        kubectl rollout status deployment/soroscan-worker -n "$NAMESPACE" --timeout=5m
        
        echo "[$(date)] Successfully scaled workers to $NEW_REPLICAS"
        
        # Send notification (optional - integrate with your notification system)
        # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"Auto-scaled workers from $CURRENT_REPLICAS to $NEW_REPLICAS due to high queue depth\"}"
        
        exit 0
    else
        echo "[$(date)] ERROR: Already at max replicas ($MAX_WORKERS). Manual intervention required."
        
        # Send alert
        # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"⚠️ ALERT: Queue depth high but already at max workers. Manual intervention needed!\"}"
        
        exit 1
    fi
else
    echo "[$(date)] Queue depth within normal range. No action needed."
    exit 0
fi

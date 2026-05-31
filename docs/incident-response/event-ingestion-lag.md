---
id: incident-response/event-ingestion-lag
title: Event Ingestion Lag Playbook
description: Response procedures for event ingestion lag exceeding threshold
sidebar_label: Event Ingestion Lag
---

# Event Ingestion Lag Playbook

## Incident Overview

**Severity**: High  
**Alert**: `EventIngestionLagHigh` or `CeleryQueueBacklog`  
**Threshold**: Ingestion lag > 5 minutes OR Celery queue depth > 10,000 tasks  
**Impact**: Events not appearing in real-time, delayed webhook deliveries

## Symptoms

- Events taking longer than expected to appear in the UI
- Celery queue depth increasing continuously
- Users reporting missing or delayed events
- Grafana dashboard shows increasing lag metric

## Immediate Actions (First 5 Minutes)

### 1. Verify the Alert

```bash
# Check current Celery queue depth
kubectl exec -it deployment/soroscan-worker -n soroscan -- celery -A soroscan inspect active_queues

# Check ingestion lag metric
curl -s http://prometheus:9090/api/v1/query?query=event_ingestion_lag_seconds | jq
```

### 2. Check System Health

```bash
# Check worker pod status
kubectl get pods -n soroscan -l app=soroscan-worker

# Check worker logs for errors
kubectl logs -n soroscan -l app=soroscan-worker --tail=100 --since=10m

# Check backend API health
kubectl logs -n soroscan -l app=soroscan-backend --tail=50 --since=5m | grep ERROR
```

### 3. Quick Triage

Determine the root cause category:
- [ ] Worker capacity issue (CPU/Memory)
- [ ] Database bottleneck
- [ ] RPC endpoint slow/unavailable
- [ ] Sudden traffic spike
- [ ] Task processing errors

## Diagnosis Steps

### Check Worker Capacity

```bash
# Check worker resource usage
kubectl top pods -n soroscan -l app=soroscan-worker

# Check worker count
kubectl get deployment soroscan-worker -n soroscan -o jsonpath='{.spec.replicas}'
```

**Expected**: CPU < 80%, Memory < 85%  
**Action if exceeded**: Scale workers (see Remediation)

### Check Database Performance

```bash
# Check active connections
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Check slow queries
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell -c "SELECT pid, now() - query_start as duration, query FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 seconds' ORDER BY duration DESC LIMIT 10;"
```

**Expected**: Active connections < 80% of max, no queries > 10s  
**Action if exceeded**: See [DB Connection Pool Playbook](./db-connection-pool-exhausted.md)

### Check RPC Endpoint

```bash
# Test RPC endpoint response time
time curl -X POST $STELLAR_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
```

**Expected**: Response < 2s  
**Action if slow**: See [RPC Endpoint Playbook](./rpc-endpoint-unavailable.md)

### Check for Task Errors

```bash
# Check Celery error rate
kubectl logs -n soroscan -l app=soroscan-worker --tail=500 | grep -i "error\|exception\|failed" | wc -l

# Check specific task failures
kubectl exec -it deployment/soroscan-worker -n soroscan -- celery -A soroscan inspect stats
```

## Remediation Actions

### Option 1: Scale Workers (Immediate Relief)

```bash
# Scale up workers by 50%
CURRENT=$(kubectl get deployment soroscan-worker -n soroscan -o jsonpath='{.spec.replicas}')
NEW=$((CURRENT * 3 / 2))
kubectl scale deployment soroscan-worker -n soroscan --replicas=$NEW

# Monitor scaling
kubectl rollout status deployment/soroscan-worker -n soroscan

# Verify queue is draining
watch -n 5 'kubectl exec -it deployment/soroscan-worker -n soroscan -- celery -A soroscan inspect active_queues'
```

**When to use**: Worker CPU/Memory high, no errors in logs

### Option 2: Restart Workers (Clear Stuck Tasks)

```bash
# Restart workers
kubectl rollout restart deployment/soroscan-worker -n soroscan

# Wait for rollout
kubectl rollout status deployment/soroscan-worker -n soroscan

# Verify workers are processing
kubectl logs -n soroscan -l app=soroscan-worker --tail=20 -f
```

**When to use**: Workers appear stuck, no progress on queue

### Option 3: Pause Non-Critical Tasks

```bash
# Temporarily disable webhook deliveries (if needed)
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from django.core.cache import cache
cache.set('webhooks_paused', True, timeout=3600)
EOF

# Verify
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell -c "from django.core.cache import cache; print(cache.get('webhooks_paused'))"
```

**When to use**: Need to prioritize event ingestion over webhooks

### Option 4: Increase Database Connections

```bash
# Check current connection pool settings
kubectl exec -it deployment/soroscan-backend -n soroscan -- env | grep DB_CONN

# Temporarily increase pool size (requires restart)
kubectl set env deployment/soroscan-backend -n soroscan DB_CONN_MAX_AGE=600 DB_POOL_SIZE=30

# Restart to apply
kubectl rollout restart deployment/soroscan-backend -n soroscan
```

**When to use**: Database connections near limit, queries waiting

## Automated Remediation

The following automation is available:

### Auto-Scaling (HPA)

```yaml
# Already configured in k8s/worker-deployment.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: soroscan-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: soroscan-worker
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: celery_queue_depth
      target:
        type: AverageValue
        averageValue: "1000"
```

### Alert Auto-Remediation Script

Create this script for automated response:

```bash
#!/bin/bash
# scripts/auto-remediate-ingestion-lag.sh

NAMESPACE="soroscan"
THRESHOLD=10000

QUEUE_DEPTH=$(kubectl exec -it deployment/soroscan-worker -n $NAMESPACE -- celery -A soroscan inspect active_queues | jq '.[] | length' | awk '{sum+=$1} END {print sum}')

if [ "$QUEUE_DEPTH" -gt "$THRESHOLD" ]; then
  echo "Queue depth $QUEUE_DEPTH exceeds threshold. Scaling workers..."
  
  CURRENT=$(kubectl get deployment soroscan-worker -n $NAMESPACE -o jsonpath='{.spec.replicas}')
  NEW=$((CURRENT + 2))
  
  if [ "$NEW" -le 20 ]; then
    kubectl scale deployment soroscan-worker -n $NAMESPACE --replicas=$NEW
    echo "Scaled workers from $CURRENT to $NEW"
  else
    echo "Already at max replicas. Manual intervention required."
    exit 1
  fi
fi
```

## Verification Steps

After remediation, verify:

```bash
# 1. Check queue is draining
kubectl exec -it deployment/soroscan-worker -n soroscan -- celery -A soroscan inspect active_queues

# 2. Check ingestion lag metric
curl -s http://prometheus:9090/api/v1/query?query=event_ingestion_lag_seconds

# 3. Verify recent events appearing
curl -s http://soroscan-backend/api/ingest/events/?limit=10 | jq '.results[0].created_at'

# 4. Check worker health
kubectl get pods -n soroscan -l app=soroscan-worker
```

**Success Criteria**:
- Queue depth decreasing
- Ingestion lag < 1 minute
- No worker errors in logs
- Recent events visible in API

## Communication Template

### Initial Alert

```
🚨 INCIDENT: Event Ingestion Lag High

Status: Investigating
Impact: Events delayed by X minutes
Started: [timestamp]

We're investigating increased event ingestion lag. 
New events may take longer to appear.

Updates: Every 15 minutes
```

### Resolution

```
✅ RESOLVED: Event Ingestion Lag

Status: Resolved
Duration: X minutes
Root Cause: [brief description]

Event ingestion has returned to normal. 
All delayed events have been processed.

Post-mortem: [link]
```

## Prevention

- **Monitoring**: Ensure `EventIngestionLagHigh` alert is configured
- **Capacity Planning**: Review worker scaling thresholds monthly
- **Load Testing**: Test ingestion capacity quarterly
- **Database Optimization**: Regular index maintenance
- **RPC Redundancy**: Configure multiple RPC endpoints

## Related Playbooks

- [Database Connection Pool Exhausted](./db-connection-pool-exhausted.md)
- [RPC Endpoint Unavailable](./rpc-endpoint-unavailable.md)
- [Webhook Delivery Failures](./webhook-delivery-failures.md)

## Post-Incident Tasks

- [ ] Document timeline and root cause
- [ ] Review worker scaling configuration
- [ ] Check for database query optimization opportunities
- [ ] Update capacity planning estimates
- [ ] Schedule post-mortem if duration > 30 minutes

---
id: incident-response/rpc-endpoint-unavailable
title: RPC Endpoint Unavailable Playbook
description: Response procedures for Stellar RPC endpoint failures
sidebar_label: RPC Endpoint Down
---

# RPC Endpoint Unavailable Playbook

## Incident Overview

**Severity**: High  
**Alert**: `RPCEndpointDown` or `RPCEndpointSlow`  
**Threshold**: RPC endpoint response time > 5s OR health check failing  
**Impact**: Event ingestion stopped, contract data unavailable

## Symptoms

- Event ingestion completely stopped
- Celery workers showing RPC timeout errors
- Contract queries failing
- Grafana dashboard shows RPC endpoint down
- Users reporting missing recent events

## Immediate Actions (First 5 Minutes)

### 1. Verify the Alert

```bash
# Test primary RPC endpoint
RPC_URL=$(kubectl get configmap soroscan-config -n soroscan -o jsonpath='{.data.STELLAR_RPC_URL}')

time curl -X POST $RPC_URL \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getHealth"
  }'
```

**Expected**: Response < 2s, status "healthy"  
**Problem**: Timeout, error, or slow response

### 2. Check RPC Endpoint Status

```bash
# Check multiple RPC methods
for method in getHealth getLatestLedger getNetwork; do
  echo "Testing $method..."
  time curl -X POST $RPC_URL \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"$method\"}" \
    -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n"
done
```

### 3. Check Worker Impact

```bash
# Check for RPC errors in worker logs
kubectl logs -n soroscan -l app=soroscan-worker --tail=200 --since=10m | grep -i "rpc\|stellar\|timeout\|connection"

# Check Celery queue depth
kubectl exec -it deployment/soroscan-worker -n soroscan -- celery -A soroscan inspect active_queues
```

## Diagnosis Steps

### Determine Failure Type

#### Complete Outage

```bash
# Test basic connectivity
curl -v $RPC_URL 2>&1 | grep -E "Connected|failed|timeout"

# Check DNS resolution
nslookup $(echo $RPC_URL | sed 's|https\?://||' | cut -d/ -f1)
```

**Indicators**: Connection refused, DNS failure, network timeout

#### Degraded Performance

```bash
# Test response times for different methods
echo "Testing RPC performance..."
for i in {1..10}; do
  time curl -X POST $RPC_URL \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"getLatestLedger"}' \
    -s -o /dev/null
done
```

**Indicators**: Slow responses (>5s), intermittent timeouts

#### Rate Limiting

```bash
# Check for rate limit responses
curl -X POST $RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}' \
  -v 2>&1 | grep -i "rate\|429\|limit"
```

**Indicators**: 429 status codes, rate limit headers

#### Specific Method Failures

```bash
# Test different RPC methods
for method in getHealth getLatestLedger getEvents getTransaction; do
  echo "Testing $method..."
  curl -X POST $RPC_URL \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"$method\"}" \
    -s | jq -r '.error // "OK"'
done
```

**Indicators**: Some methods work, others fail

### Check RPC Provider Status

```bash
# Check if using public RPC (e.g., Stellar public RPC)
echo "RPC URL: $RPC_URL"

# Check provider status page (if available)
# For Stellar: https://status.stellar.org
# For custom provider: check their status page
```

## Remediation Actions

### Option 1: Failover to Backup RPC Endpoint (Immediate)

```bash
# List configured RPC endpoints
kubectl get configmap soroscan-config -n soroscan -o jsonpath='{.data}' | grep RPC

# Update to backup RPC endpoint
kubectl patch configmap soroscan-config -n soroscan --type merge -p '{"data":{"STELLAR_RPC_URL":"https://backup-rpc.stellar.org"}}'

# Restart workers to pick up new config
kubectl rollout restart deployment/soroscan-worker -n soroscan

# Verify workers using new endpoint
sleep 30
kubectl logs -n soroscan -l app=soroscan-worker --tail=20 | grep -i "rpc\|stellar"
```

**When to use**: Primary RPC down, backup available  
**Risk**: Low - if backup is tested and ready

### Option 2: Enable RPC Endpoint Rotation (Automatic)

```bash
# Update config with multiple RPC endpoints
kubectl patch configmap soroscan-config -n soroscan --type merge -p '{
  "data": {
    "STELLAR_RPC_URLS": "https://rpc1.stellar.org,https://rpc2.stellar.org,https://rpc3.stellar.org",
    "RPC_FAILOVER_ENABLED": "true"
  }
}'

# Restart workers
kubectl rollout restart deployment/soroscan-worker -n soroscan
```

**When to use**: Multiple RPC endpoints available, want automatic failover  
**Risk**: Low - requires code support for rotation

### Option 3: Reduce RPC Request Rate (Temporary)

```bash
# Reduce worker concurrency to lower RPC load
kubectl set env deployment/soroscan-worker -n soroscan \
  CELERY_WORKER_CONCURRENCY=2 \
  RPC_REQUEST_TIMEOUT=30

# Scale down workers
CURRENT=$(kubectl get deployment soroscan-worker -n soroscan -o jsonpath='{.spec.replicas}')
NEW=$((CURRENT / 2))
kubectl scale deployment soroscan-worker -n soroscan --replicas=$NEW
```

**When to use**: RPC rate limited or degraded  
**Risk**: Medium - reduces ingestion capacity

### Option 4: Pause Event Ingestion (Emergency)

```bash
# Pause Celery workers
kubectl scale deployment soroscan-worker -n soroscan --replicas=0

# Verify workers stopped
kubectl get pods -n soroscan -l app=soroscan-worker

# Update status page
echo "Event ingestion paused due to RPC issues"
```

**When to use**: RPC completely unavailable, no backup  
**Risk**: High - stops all event ingestion

### Option 5: Switch to Alternative Data Source

```bash
# If using Horizon as backup
kubectl patch configmap soroscan-config -n soroscan --type merge -p '{
  "data": {
    "DATA_SOURCE": "horizon",
    "HORIZON_URL": "https://horizon.stellar.org"
  }
}'

# Restart workers
kubectl rollout restart deployment/soroscan-worker -n soroscan
```

**When to use**: RPC down, Horizon available as alternative  
**Risk**: Medium - different data format, may need code changes

## Automated Remediation

### RPC Health Check & Failover Script

```python
# soroscan/ingest/rpc_failover.py

import requests
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class RPCFailover:
    def __init__(self):
        self.endpoints = settings.STELLAR_RPC_URLS.split(',')
        self.timeout = 5
        self.cache_key = 'active_rpc_endpoint'
    
    def get_active_endpoint(self):
        """Get currently active RPC endpoint"""
        cached = cache.get(self.cache_key)
        if cached:
            return cached
        return self.endpoints[0]
    
    def check_health(self, endpoint):
        """Check if RPC endpoint is healthy"""
        try:
            response = requests.post(
                endpoint,
                json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                timeout=self.timeout
            )
            return response.status_code == 200 and response.json().get('result', {}).get('status') == 'healthy'
        except Exception as e:
            logger.warning(f"RPC health check failed for {endpoint}: {e}")
            return False
    
    def failover(self):
        """Find and switch to healthy RPC endpoint"""
        current = self.get_active_endpoint()
        
        # Check current endpoint first
        if self.check_health(current):
            return current
        
        logger.warning(f"Current RPC endpoint {current} is unhealthy, failing over...")
        
        # Try other endpoints
        for endpoint in self.endpoints:
            if endpoint == current:
                continue
            
            if self.check_health(endpoint):
                logger.info(f"Failing over to {endpoint}")
                cache.set(self.cache_key, endpoint, timeout=300)  # 5 minutes
                return endpoint
        
        logger.error("All RPC endpoints are unhealthy!")
        return None
    
    def get_endpoint(self):
        """Get healthy RPC endpoint with automatic failover"""
        endpoint = self.get_active_endpoint()
        
        # Periodically check health
        health_check_key = f'rpc_health_check_{endpoint}'
        if not cache.get(health_check_key):
            if not self.check_health(endpoint):
                endpoint = self.failover()
            cache.set(health_check_key, True, timeout=60)  # Check every minute
        
        return endpoint

# Usage in tasks
from soroscan.ingest.rpc_failover import RPCFailover

@shared_task
def ingest_events():
    rpc = RPCFailover()
    endpoint = rpc.get_endpoint()
    
    if not endpoint:
        logger.error("No healthy RPC endpoint available")
        raise Exception("RPC unavailable")
    
    # Use endpoint for requests
    response = requests.post(endpoint, json=payload)
```

### Prometheus Alert Rules

```yaml
groups:
  - name: rpc_alerts
    interval: 30s
    rules:
      - alert: RPCEndpointSlow
        expr: |
          histogram_quantile(0.95, 
            rate(rpc_request_duration_seconds_bucket[5m])
          ) > 5
        for: 5m
        labels:
          severity: medium
          component: rpc
        annotations:
          summary: "RPC endpoint responding slowly"
          description: "RPC p95 latency is {{ $value }}s (threshold: 5s)"
          runbook: "https://docs.soroscan.io/incident-response/rpc-endpoint-unavailable"
      
      - alert: RPCEndpointDown
        expr: up{job="rpc-endpoint"} == 0
        for: 2m
        labels:
          severity: high
          component: rpc
        annotations:
          summary: "RPC endpoint is down"
          description: "RPC endpoint {{ $labels.instance }} has been down for 2 minutes"
          runbook: "https://docs.soroscan.io/incident-response/rpc-endpoint-unavailable"
      
      - alert: RPCErrorRateHigh
        expr: |
          (
            rate(rpc_requests_failed_total[5m])
            /
            rate(rpc_requests_total[5m])
          ) > 0.10
        for: 5m
        labels:
          severity: high
          component: rpc
        annotations:
          summary: "High RPC error rate"
          description: "RPC error rate is {{ $value | humanizePercentage }} (threshold: 10%)"
          runbook: "https://docs.soroscan.io/incident-response/rpc-endpoint-unavailable"
```

### Auto-Failover CronJob

```yaml
# k8s/rpc-health-check-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: rpc-health-check
  namespace: soroscan
spec:
  schedule: "*/2 * * * *"  # Every 2 minutes
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: health-check
            image: soroscan-backend:latest
            command:
            - /bin/bash
            - -c
            - |
              python manage.py shell <<EOF
              from soroscan.ingest.rpc_failover import RPCFailover
              rpc = RPCFailover()
              endpoint = rpc.failover()
              if endpoint:
                  print(f"Active RPC endpoint: {endpoint}")
              else:
                  print("ERROR: No healthy RPC endpoints!")
                  exit(1)
              EOF
          restartPolicy: OnFailure
```

### RPC Endpoint Monitoring

```python
# soroscan/ingest/monitoring.py

from prometheus_client import Histogram, Counter

rpc_request_duration = Histogram(
    'rpc_request_duration_seconds',
    'RPC request duration',
    ['method', 'endpoint']
)

rpc_requests_total = Counter(
    'rpc_requests_total',
    'Total RPC requests',
    ['method', 'endpoint', 'status']
)

def make_rpc_request(endpoint, method, params):
    with rpc_request_duration.labels(method=method, endpoint=endpoint).time():
        try:
            response = requests.post(endpoint, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            })
            
            status = 'success' if response.status_code == 200 else 'error'
            rpc_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
            
            return response
        except Exception as e:
            rpc_requests_total.labels(method=method, endpoint=endpoint, status='error').inc()
            raise
```

## Verification Steps

After remediation:

```bash
# 1. Test RPC endpoint
time curl -X POST $RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'

# 2. Check workers are processing
kubectl logs -n soroscan -l app=soroscan-worker --tail=50 --since=5m | grep -i "processing\|ingested"

# 3. Check Celery queue
kubectl exec -it deployment/soroscan-worker -n soroscan -- celery -A soroscan inspect active_queues

# 4. Verify recent events
curl -s http://soroscan-backend/api/ingest/events/?limit=5 | jq '.results[0].created_at'
```

**Success Criteria**:
- RPC responding < 2s
- Workers processing events
- Queue depth stable or decreasing
- Recent events appearing

## Communication Template

### Initial Alert

```
🚨 INCIDENT: RPC Endpoint Issues

Status: Investigating
Impact: Event ingestion delayed
Started: [timestamp]

We're experiencing issues with our Stellar RPC endpoint.
Event ingestion may be delayed.

Updates: Every 15 minutes
```

### Failover Notification

```
🔄 UPDATE: RPC Failover

Status: Mitigated
Action: Switched to backup RPC endpoint

Event ingestion has resumed on backup endpoint.
Monitoring for stability.

Updates: Every 30 minutes
```

### Resolution

```
✅ RESOLVED: RPC Endpoint Issues

Status: Resolved
Duration: X minutes
Root Cause: [brief description]

RPC endpoint has been restored/failed over.
Event ingestion is operating normally.

Actions taken:
- [list actions]

Prevention:
- Implemented automatic RPC failover
- Added additional backup endpoints
```

## Prevention

- **Multiple Endpoints**: Configure 3+ RPC endpoints for redundancy
- **Automatic Failover**: Implement RPC health checks and automatic failover
- **Monitoring**: Alert on RPC latency and error rates
- **Rate Limiting**: Implement client-side rate limiting
- **Caching**: Cache RPC responses where appropriate
- **SLA Monitoring**: Track RPC provider SLA compliance
- **Backup Data Source**: Have Horizon or alternative ready as backup

## Related Playbooks

- [Event Ingestion Lag](./event-ingestion-lag.md) - Often caused by RPC issues
- [Database Connection Pool](./db-connection-pool-exhausted.md) - Can be affected by RPC slowness

## Post-Incident Tasks

- [ ] Document RPC provider and failure mode
- [ ] Review RPC endpoint configuration
- [ ] Test automatic failover mechanism
- [ ] Add additional backup RPC endpoints
- [ ] Update RPC provider SLA documentation
- [ ] Consider self-hosted RPC node
- [ ] Schedule post-mortem if duration > 30 minutes

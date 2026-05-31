---
id: incident-response/webhook-delivery-failures
title: Webhook Delivery Failure Burst Playbook
description: Response procedures for webhook delivery failure spikes
sidebar_label: Webhook Failures
---

# Webhook Delivery Failure Burst Playbook

## Incident Overview

**Severity**: Medium  
**Alert**: `WebhookFailureRateHigh`  
**Threshold**: Webhook failure rate > 10% OR 5x increase in failures  
**Impact**: Customers not receiving webhook notifications

## Symptoms

- Spike in webhook delivery failures
- Customer reports of missing webhooks
- Grafana dashboard shows increased failure rate
- Webhook retry queue growing

## Immediate Actions (First 5 Minutes)

### 1. Verify the Alert

```bash
# Check webhook failure rate (last 5 minutes)
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from soroscan.ingest.models import WebhookDeliveryAttempt
from django.utils import timezone
from datetime import timedelta

five_min_ago = timezone.now() - timedelta(minutes=5)
total = WebhookDeliveryAttempt.objects.filter(created_at__gte=five_min_ago).count()
failed = WebhookDeliveryAttempt.objects.filter(created_at__gte=five_min_ago, status='failed').count()
print(f"Total: {total}, Failed: {failed}, Rate: {failed/total*100:.2f}%")
EOF
```

### 2. Identify Affected Webhooks

```bash
# Get top failing webhook endpoints
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from soroscan.ingest.models import WebhookDeliveryAttempt, Webhook
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

five_min_ago = timezone.now() - timedelta(minutes=5)
failing = WebhookDeliveryAttempt.objects.filter(
    created_at__gte=five_min_ago,
    status='failed'
).values('webhook__url').annotate(
    count=Count('id')
).order_by('-count')[:10]

for item in failing:
    print(f"{item['webhook__url']}: {item['count']} failures")
EOF
```

### 3. Check Error Patterns

```bash
# Check common error messages
kubectl logs -n soroscan -l app=soroscan-worker --tail=200 | grep -i "webhook.*error" | sort | uniq -c | sort -rn | head -10
```

## Diagnosis Steps

### Determine Failure Type

#### Network/Timeout Issues

```bash
# Check for timeout errors
kubectl logs -n soroscan -l app=soroscan-worker --tail=500 | grep -i "webhook.*timeout\|connection.*refused\|connection.*reset"
```

**Indicators**: Connection timeouts, DNS failures, connection refused

#### Customer Endpoint Issues

```bash
# Test specific failing endpoint
WEBHOOK_URL="https://customer-endpoint.example.com/webhook"
time curl -X POST $WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: test" \
  -d '{"test": true}' \
  -v
```

**Indicators**: 4xx/5xx responses, slow response times (>30s)

#### Rate Limiting

```bash
# Check for 429 responses
kubectl logs -n soroscan -l app=soroscan-worker --tail=500 | grep -i "webhook.*429\|rate.*limit"
```

**Indicators**: 429 status codes, rate limit errors

#### Certificate/SSL Issues

```bash
# Check SSL certificate validity
echo | openssl s_client -servername customer-endpoint.example.com -connect customer-endpoint.example.com:443 2>/dev/null | openssl x509 -noout -dates
```

**Indicators**: SSL handshake failures, certificate expired

## Remediation Actions

### Option 1: Pause Specific Failing Webhooks (Immediate)

```bash
# Disable specific webhook temporarily
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from soroscan.ingest.models import Webhook

# Replace with actual failing webhook ID
webhook_id = "WEBHOOK_ID_HERE"
webhook = Webhook.objects.get(id=webhook_id)
webhook.is_active = False
webhook.save()
print(f"Disabled webhook: {webhook.url}")
EOF
```

**When to use**: Single customer endpoint causing majority of failures

### Option 2: Increase Retry Backoff (Reduce Load)

```bash
# Temporarily increase retry delay
kubectl set env deployment/soroscan-worker -n soroscan \
  WEBHOOK_RETRY_DELAY=300 \
  WEBHOOK_MAX_RETRIES=3

# Restart workers to apply
kubectl rollout restart deployment/soroscan-worker -n soroscan
```

**When to use**: Customer endpoints temporarily overloaded

### Option 3: Enable Circuit Breaker (Automatic)

```bash
# Enable circuit breaker for failing endpoints
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from django.core.cache import cache
from soroscan.ingest.models import WebhookDeliveryAttempt
from django.utils import timezone
from datetime import timedelta

# Get webhooks with >50% failure rate in last 10 minutes
ten_min_ago = timezone.now() - timedelta(minutes=10)
failing_webhooks = WebhookDeliveryAttempt.objects.filter(
    created_at__gte=ten_min_ago
).values('webhook_id').annotate(
    total=Count('id'),
    failed=Count('id', filter=Q(status='failed'))
).filter(failed__gt=F('total') * 0.5)

for item in failing_webhooks:
    cache_key = f"webhook_circuit_breaker_{item['webhook_id']}"
    cache.set(cache_key, True, timeout=600)  # 10 minutes
    print(f"Circuit breaker enabled for webhook {item['webhook_id']}")
EOF
```

**When to use**: Multiple endpoints failing, need automatic protection

### Option 4: Notify Affected Customers

```bash
# Get list of affected customers
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from soroscan.ingest.models import Webhook, WebhookDeliveryAttempt
from django.utils import timezone
from datetime.timedelta import timedelta

ten_min_ago = timezone.now() - timedelta(minutes=10)
affected_webhooks = Webhook.objects.filter(
    deliveryattempt__created_at__gte=ten_min_ago,
    deliveryattempt__status='failed'
).distinct()

for webhook in affected_webhooks:
    print(f"Customer: {webhook.organization.name}, Email: {webhook.organization.contact_email}, URL: {webhook.url}")
EOF
```

**When to use**: Customer endpoint issues, need to notify them

## Automated Remediation

### Circuit Breaker Implementation

Add to `soroscan/ingest/tasks.py`:

```python
from django.core.cache import cache
from datetime import timedelta

def should_skip_webhook(webhook_id):
    """Check if webhook is in circuit breaker state"""
    cache_key = f"webhook_circuit_breaker_{webhook_id}"
    return cache.get(cache_key, False)

def record_webhook_failure(webhook_id):
    """Record failure and potentially trigger circuit breaker"""
    cache_key = f"webhook_failures_{webhook_id}"
    failures = cache.get(cache_key, 0) + 1
    cache.set(cache_key, failures, timeout=600)  # 10 minutes
    
    # Trigger circuit breaker after 10 failures in 10 minutes
    if failures >= 10:
        breaker_key = f"webhook_circuit_breaker_{webhook_id}"
        cache.set(breaker_key, True, timeout=600)
        logger.warning(f"Circuit breaker triggered for webhook {webhook_id}")
        return True
    return False

@shared_task(bind=True, max_retries=3)
def deliver_webhook(self, webhook_id, event_data):
    # Check circuit breaker
    if should_skip_webhook(webhook_id):
        logger.info(f"Skipping webhook {webhook_id} - circuit breaker active")
        return
    
    try:
        # Existing webhook delivery logic
        response = requests.post(webhook.url, json=event_data, timeout=30)
        response.raise_for_status()
        
        # Reset failure counter on success
        cache.delete(f"webhook_failures_{webhook_id}")
        
    except Exception as e:
        if record_webhook_failure(webhook_id):
            # Circuit breaker triggered, don't retry
            return
        raise self.retry(exc=e, countdown=60)
```

### Auto-Disable Script

```bash
#!/bin/bash
# scripts/auto-disable-failing-webhooks.sh

NAMESPACE="soroscan"
FAILURE_THRESHOLD=80  # 80% failure rate

kubectl exec -it deployment/soroscan-backend -n $NAMESPACE -- python manage.py shell <<EOF
from soroscan.ingest.models import Webhook, WebhookDeliveryAttempt
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, F

# Check last 15 minutes
fifteen_min_ago = timezone.now() - timedelta(minutes=15)

failing_webhooks = Webhook.objects.filter(
    deliveryattempt__created_at__gte=fifteen_min_ago,
    is_active=True
).annotate(
    total_attempts=Count('deliveryattempt'),
    failed_attempts=Count('deliveryattempt', filter=Q(deliveryattempt__status='failed'))
).filter(
    total_attempts__gte=10,  # At least 10 attempts
    failed_attempts__gte=F('total_attempts') * $FAILURE_THRESHOLD / 100
)

for webhook in failing_webhooks:
    webhook.is_active = False
    webhook.save()
    print(f"Auto-disabled webhook {webhook.id}: {webhook.url}")
    
    # TODO: Send notification to customer
EOF
```

### Prometheus Alert Rule

Add to Prometheus configuration:

```yaml
groups:
  - name: webhook_alerts
    interval: 1m
    rules:
      - alert: WebhookFailureRateHigh
        expr: |
          (
            rate(webhook_delivery_failed_total[5m]) 
            / 
            rate(webhook_delivery_total[5m])
          ) > 0.10
        for: 5m
        labels:
          severity: medium
          component: webhooks
        annotations:
          summary: "High webhook failure rate detected"
          description: "Webhook failure rate is {{ $value | humanizePercentage }} (threshold: 10%)"
          runbook: "https://docs.soroscan.io/incident-response/webhook-delivery-failures"
      
      - alert: WebhookFailureBurst
        expr: |
          (
            rate(webhook_delivery_failed_total[5m])
            /
            rate(webhook_delivery_failed_total[1h] offset 1h)
          ) > 5
        for: 2m
        labels:
          severity: medium
          component: webhooks
        annotations:
          summary: "Webhook failure burst detected"
          description: "Webhook failures increased by {{ $value }}x compared to 1 hour ago"
          runbook: "https://docs.soroscan.io/incident-response/webhook-delivery-failures"
```

## Verification Steps

After remediation:

```bash
# 1. Check current failure rate
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from soroscan.ingest.models import WebhookDeliveryAttempt
from django.utils import timezone
from datetime import timedelta

five_min_ago = timezone.now() - timedelta(minutes=5)
total = WebhookDeliveryAttempt.objects.filter(created_at__gte=five_min_ago).count()
failed = WebhookDeliveryAttempt.objects.filter(created_at__gte=five_min_ago, status='failed').count()
print(f"Current failure rate: {failed/total*100:.2f}%")
EOF

# 2. Check retry queue depth
kubectl exec -it deployment/soroscan-worker -n soroscan -- celery -A soroscan inspect active_queues | grep webhook

# 3. Verify no new errors
kubectl logs -n soroscan -l app=soroscan-worker --tail=50 --since=5m | grep -i "webhook.*error"
```

**Success Criteria**:
- Failure rate < 5%
- No new error patterns
- Retry queue stable or decreasing
- Customer endpoints responding

## Communication Template

### Initial Alert

```
⚠️ INCIDENT: Webhook Delivery Issues

Status: Investigating
Impact: Some webhooks may be delayed or failing
Started: [timestamp]

We're investigating increased webhook delivery failures.
Affected endpoints: [list or "investigating"]

Updates: Every 15 minutes
```

### Customer Notification (if their endpoint is down)

```
Subject: Action Required: Webhook Endpoint Issues

Hi [Customer],

We've detected that your webhook endpoint at [URL] is 
experiencing issues:

Error: [error message]
Failure rate: [X]%
Started: [timestamp]

Please check:
- Endpoint is accessible
- SSL certificate is valid
- Rate limits are not exceeded
- Server has capacity

We've temporarily paused deliveries to prevent further 
failures. Please reply when resolved.

Best regards,
SoroScan Team
```

### Resolution

```
✅ RESOLVED: Webhook Delivery Issues

Status: Resolved
Duration: X minutes
Root Cause: [brief description]

Webhook deliveries have returned to normal.
Failed webhooks will be retried automatically.

Post-mortem: [link if needed]
```

## Prevention

- **Monitoring**: Configure `WebhookFailureRateHigh` and `WebhookFailureBurst` alerts
- **Circuit Breaker**: Implement automatic circuit breaker (see above)
- **Customer Validation**: Validate webhook endpoints before activation
- **Health Checks**: Periodic health checks for webhook endpoints
- **Documentation**: Provide webhook best practices to customers
- **Rate Limiting**: Implement per-customer webhook rate limits

## Related Playbooks

- [Event Ingestion Lag](./event-ingestion-lag.md) - May cause webhook delays
- [Database Connection Pool](./db-connection-pool-exhausted.md) - Can affect webhook processing

## Post-Incident Tasks

- [ ] Document affected customers and endpoints
- [ ] Review circuit breaker thresholds
- [ ] Update customer webhook documentation
- [ ] Check if auto-remediation worked as expected
- [ ] Follow up with affected customers
- [ ] Update webhook retry configuration if needed

#!/bin/bash
# Auto-remediation script for webhook delivery failures
# Triggered by Prometheus alert: WebhookFailureRateHigh

set -e

NAMESPACE="${NAMESPACE:-soroscan}"
FAILURE_RATE_THRESHOLD="${FAILURE_RATE_THRESHOLD:-50}"  # 50%
MIN_ATTEMPTS="${MIN_ATTEMPTS:-10}"
LOOKBACK_MINUTES="${LOOKBACK_MINUTES:-15}"

echo "[$(date)] Starting auto-remediation for webhook failures..."

# Function to disable failing webhooks
disable_failing_webhooks() {
    kubectl exec -it deployment/soroscan-backend -n "$NAMESPACE" -- python manage.py shell <<EOF
from soroscan.ingest.models import Webhook, WebhookDeliveryAttempt
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, F

lookback = timezone.now() - timedelta(minutes=$LOOKBACK_MINUTES)

# Find webhooks with high failure rate
failing_webhooks = Webhook.objects.filter(
    deliveryattempt__created_at__gte=lookback,
    is_active=True
).annotate(
    total_attempts=Count('deliveryattempt'),
    failed_attempts=Count('deliveryattempt', filter=Q(deliveryattempt__status='failed'))
).filter(
    total_attempts__gte=$MIN_ATTEMPTS,
    failed_attempts__gte=F('total_attempts') * $FAILURE_RATE_THRESHOLD / 100
)

disabled_count = 0
for webhook in failing_webhooks:
    failure_rate = (webhook.failed_attempts / webhook.total_attempts) * 100
    print(f"Disabling webhook {webhook.id} ({webhook.url}): {failure_rate:.1f}% failure rate")
    
    webhook.is_active = False
    webhook.save()
    disabled_count += 1

print(f"Disabled {disabled_count} webhooks")
exit(0 if disabled_count > 0 else 1)
EOF
}

# Function to enable circuit breaker
enable_circuit_breaker() {
    kubectl exec -it deployment/soroscan-backend -n "$NAMESPACE" -- python manage.py shell <<EOF
from django.core.cache import cache
from soroscan.ingest.models import WebhookDeliveryAttempt
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q

lookback = timezone.now() - timedelta(minutes=$LOOKBACK_MINUTES)

# Get webhooks with failures
failing_webhooks = WebhookDeliveryAttempt.objects.filter(
    created_at__gte=lookback,
    status='failed'
).values('webhook_id').annotate(
    count=Count('id')
).filter(count__gte=5)

breaker_count = 0
for item in failing_webhooks:
    cache_key = f"webhook_circuit_breaker_{item['webhook_id']}"
    cache.set(cache_key, True, timeout=600)  # 10 minutes
    breaker_count += 1

print(f"Enabled circuit breaker for {breaker_count} webhooks")
EOF
}

# Get current failure rate
FAILURE_STATS=$(kubectl exec -it deployment/soroscan-backend -n "$NAMESPACE" -- python manage.py shell <<EOF
from soroscan.ingest.models import WebhookDeliveryAttempt
from django.utils import timezone
from datetime import timedelta

lookback = timezone.now() - timedelta(minutes=$LOOKBACK_MINUTES)
total = WebhookDeliveryAttempt.objects.filter(created_at__gte=lookback).count()
failed = WebhookDeliveryAttempt.objects.filter(created_at__gte=lookback, status='failed').count()

if total > 0:
    rate = (failed / total) * 100
    print(f"{rate:.1f}")
else:
    print("0")
EOF
)

echo "[$(date)] Current failure rate: ${FAILURE_STATS}%"

# Check if failure rate exceeds threshold
if (( $(echo "$FAILURE_STATS > $FAILURE_RATE_THRESHOLD" | bc -l) )); then
    echo "[$(date)] Failure rate exceeds threshold. Taking action..."
    
    # Enable circuit breaker first (less disruptive)
    echo "[$(date)] Enabling circuit breaker..."
    enable_circuit_breaker
    
    # If still high, disable failing webhooks
    echo "[$(date)] Disabling failing webhooks..."
    if disable_failing_webhooks; then
        echo "[$(date)] Successfully disabled failing webhooks"
        
        # Send notification
        # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"Auto-disabled failing webhooks due to high failure rate (${FAILURE_STATS}%)\"}"
        
        exit 0
    else
        echo "[$(date)] No webhooks disabled (none met criteria)"
        exit 0
    fi
else
    echo "[$(date)] Failure rate within acceptable range. No action needed."
    exit 0
fi

# Incident Response Automation Scripts

This directory contains automated remediation scripts for common production incidents.

## Scripts

### 1. auto-remediate-ingestion-lag.sh

**Purpose**: Automatically scale Celery workers when event ingestion lag is high.

**Triggered by**: `EventIngestionLagHigh` or `CeleryQueueBacklog` Prometheus alerts

**What it does**:
- Checks Celery queue depth
- Scales workers up by 2 replicas if queue exceeds threshold
- Respects maximum worker limit (default: 20)

**Usage**:
```bash
# Manual execution
NAMESPACE=soroscan QUEUE_THRESHOLD=10000 MAX_WORKERS=20 ./auto-remediate-ingestion-lag.sh

# Environment variables
NAMESPACE          - Kubernetes namespace (default: soroscan)
QUEUE_THRESHOLD    - Queue depth threshold (default: 10000)
MAX_WORKERS        - Maximum worker replicas (default: 20)
SCALE_INCREMENT    - Number of replicas to add (default: 2)
```

**Playbook**: [Event Ingestion Lag](../docs/incident-response/event-ingestion-lag.md)

---

### 2. auto-remediate-webhook-failures.sh

**Purpose**: Automatically handle webhook delivery failure bursts.

**Triggered by**: `WebhookFailureRateHigh` or `WebhookFailureBurst` Prometheus alerts

**What it does**:
- Checks webhook failure rate
- Enables circuit breaker for failing webhooks
- Disables webhooks with >50% failure rate
- Prevents cascading failures

**Usage**:
```bash
# Manual execution
NAMESPACE=soroscan FAILURE_RATE_THRESHOLD=50 ./auto-remediate-webhook-failures.sh

# Environment variables
NAMESPACE                - Kubernetes namespace (default: soroscan)
FAILURE_RATE_THRESHOLD   - Failure rate % to trigger action (default: 50)
MIN_ATTEMPTS             - Minimum attempts before disabling (default: 10)
LOOKBACK_MINUTES         - Time window to analyze (default: 15)
```

**Playbook**: [Webhook Delivery Failures](../docs/incident-response/webhook-delivery-failures.md)

---

### 3. auto-remediate-db-connections.sh

**Purpose**: Automatically clean up database connection pool issues.

**Triggered by**: `DatabaseConnectionPoolNearLimit` or `DatabaseIdleInTransactionHigh` alerts

**What it does**:
- Kills idle in transaction connections (>5 minutes)
- Kills very old idle connections (>30 minutes)
- Prevents connection pool exhaustion

**Usage**:
```bash
# Manual execution
NAMESPACE=soroscan CONNECTION_THRESHOLD_PERCENT=80 ./auto-remediate-db-connections.sh

# Environment variables
NAMESPACE                      - Kubernetes namespace (default: soroscan)
IDLE_THRESHOLD_SECONDS         - Idle time before killing (default: 300)
CONNECTION_THRESHOLD_PERCENT   - Connection usage % to trigger (default: 80)
```

**Playbook**: [Database Connection Pool Exhausted](../docs/incident-response/db-connection-pool-exhausted.md)

---

### 4. auto-remediate-rpc-failure.sh

**Purpose**: Automatically failover to backup RPC endpoint when primary fails.

**Triggered by**: `RPCEndpointDown` or `RPCErrorRateHigh` Prometheus alerts

**What it does**:
- Tests current RPC endpoint health
- Finds healthy backup RPC endpoint
- Updates ConfigMap with new endpoint
- Restarts workers to apply change

**Usage**:
```bash
# Manual execution
NAMESPACE=soroscan RPC_TIMEOUT=5 ./auto-remediate-rpc-failure.sh

# Environment variables
NAMESPACE     - Kubernetes namespace (default: soroscan)
RPC_TIMEOUT   - RPC health check timeout in seconds (default: 5)
```

**Prerequisites**:
- Backup RPC URLs must be configured in ConfigMap:
```bash
kubectl patch configmap soroscan-config -n soroscan --type merge -p '{
  "data": {
    "STELLAR_RPC_BACKUP_URLS": "https://rpc1.stellar.org,https://rpc2.stellar.org"
  }
}'
```

**Playbook**: [RPC Endpoint Unavailable](../docs/incident-response/rpc-endpoint-unavailable.md)

---

## Installation

### 1. Make Scripts Executable

```bash
chmod +x scripts/incident-response/*.sh
```

### 2. Test Scripts (Dry Run)

```bash
# Test with safe thresholds that won't trigger actions
NAMESPACE=soroscan QUEUE_THRESHOLD=999999 ./auto-remediate-ingestion-lag.sh
NAMESPACE=soroscan FAILURE_RATE_THRESHOLD=99 ./auto-remediate-webhook-failures.sh
NAMESPACE=soroscan CONNECTION_THRESHOLD_PERCENT=99 ./auto-remediate-db-connections.sh
NAMESPACE=soroscan ./auto-remediate-rpc-failure.sh
```

### 3. Configure Alertmanager (Optional)

To automatically execute scripts when alerts fire:

```yaml
# alertmanager-config.yaml
receivers:
  - name: 'auto-remediation'
    webhook_configs:
      - url: 'http://remediation-service/webhook'
        send_resolved: true

route:
  routes:
    - match:
        auto_remediation: 'true'
      receiver: 'auto-remediation'
      continue: true
```

## Monitoring

Each script logs its actions. Monitor execution:

```bash
# View script execution logs
kubectl logs -n soroscan -l app=remediation-service --tail=100

# Check if auto-remediation is working
kubectl get events -n soroscan --sort-by='.lastTimestamp' | grep -i remediation
```

## Safety Features

All scripts include:
- ✅ Threshold checks before taking action
- ✅ Maximum limits to prevent over-scaling
- ✅ Verification steps after remediation
- ✅ Detailed logging of all actions
- ✅ Exit codes for monitoring (0=success, 1=failure)

## Notifications

To enable Slack notifications, uncomment and configure the webhook URL in each script:

```bash
# Add to each script
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Uncomment notification lines in scripts
curl -X POST "$SLACK_WEBHOOK_URL" -d '{"text":"Auto-remediation message"}'
```

## Troubleshooting

### Script Fails to Execute

```bash
# Check permissions
ls -la scripts/incident-response/

# Check kubectl access
kubectl auth can-i get pods -n soroscan

# Check script syntax
bash -n scripts/incident-response/auto-remediate-ingestion-lag.sh
```

### Script Executes But No Action Taken

```bash
# Check thresholds
echo "Current queue depth: $(kubectl exec -it deployment/soroscan-worker -n soroscan -- celery -A soroscan inspect active_queues)"

# Run with debug output
bash -x scripts/incident-response/auto-remediate-ingestion-lag.sh
```

### Script Takes Action But Issue Persists

- Check the corresponding playbook for manual intervention steps
- Review logs for errors: `kubectl logs -n soroscan -l app=soroscan-worker --tail=100`
- Escalate to on-call engineer

## Best Practices

1. **Test in Staging First**: Always test scripts in staging before production
2. **Monitor Execution**: Set up alerts for script failures
3. **Review Regularly**: Review script effectiveness monthly
4. **Update Thresholds**: Adjust thresholds based on your workload
5. **Document Changes**: Update playbooks when modifying scripts

## Related Documentation

- [Incident Response Overview](../docs/incident-response/README.md)
- [Prometheus Alert Rules](../k8s/prometheus-incident-alerts.yaml)
- [Deployment Runbooks](../docs/deployment/runbooks.md)

## Support

For issues with automation scripts:
- Check the corresponding playbook for manual procedures
- Review script logs for error messages
- Contact on-call engineer via PagerDuty
- Post in #incidents Slack channel

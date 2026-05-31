---
id: incident-response/db-connection-pool-exhausted
title: Database Connection Pool Exhausted Playbook
description: Response procedures for database connection pool exhaustion
sidebar_label: DB Connection Pool
---

# Database Connection Pool Exhausted Playbook

## Incident Overview

**Severity**: Critical  
**Alert**: `DatabaseConnectionPoolExhausted` or `DatabaseConnectionPoolNearLimit`  
**Threshold**: Active connections > 90% of max pool size  
**Impact**: API requests failing, 500 errors, service degradation

## Symptoms

- API returning 500 errors with "too many connections" or "connection pool exhausted"
- Application logs showing connection timeout errors
- Grafana dashboard shows DB connections at or near limit
- Slow response times across all endpoints

## Immediate Actions (First 5 Minutes)

### 1. Verify the Alert

```bash
# Check current connection count
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell <<EOF
SELECT 
  count(*) as total_connections,
  count(*) FILTER (WHERE state = 'active') as active,
  count(*) FILTER (WHERE state = 'idle') as idle,
  count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity 
WHERE datname = current_database();
EOF

# Check max connections setting
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell -c "SHOW max_connections;"
```

### 2. Assess Impact

```bash
# Check API error rate
kubectl logs -n soroscan -l app=soroscan-backend --tail=100 --since=5m | grep -c "500\|connection.*pool\|too many connections"

# Check if requests are queuing
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from django.db import connection
print(f"Connection pool size: {connection.settings_dict.get('CONN_MAX_AGE')}")
print(f"Current connections: {len(connection.queries)}")
EOF
```

### 3. Identify Connection Leaks

```bash
# Find long-running queries
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell <<EOF
SELECT 
  pid,
  usename,
  application_name,
  client_addr,
  state,
  now() - query_start as duration,
  query
FROM pg_stat_activity 
WHERE state != 'idle' 
  AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC 
LIMIT 20;
EOF
```

## Diagnosis Steps

### Check Connection Distribution

```bash
# Connections by application/pod
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell <<EOF
SELECT 
  application_name,
  state,
  count(*) as connections
FROM pg_stat_activity 
WHERE datname = current_database()
GROUP BY application_name, state
ORDER BY connections DESC;
EOF
```

**Expected**: Connections evenly distributed across pods  
**Problem**: One pod holding many connections

### Check for Idle Transactions

```bash
# Find idle transactions (connection leaks)
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell <<EOF
SELECT 
  pid,
  usename,
  application_name,
  state,
  now() - state_change as idle_duration,
  query
FROM pg_stat_activity 
WHERE state = 'idle in transaction'
  AND now() - state_change > interval '5 minutes'
ORDER BY idle_duration DESC;
EOF
```

**Expected**: No idle transactions > 5 minutes  
**Problem**: Many idle transactions indicate connection leaks

### Check Connection Pool Configuration

```bash
# Check Django connection settings
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py shell <<EOF
from django.conf import settings
db_config = settings.DATABASES['default']
print(f"CONN_MAX_AGE: {db_config.get('CONN_MAX_AGE')}")
print(f"CONN_HEALTH_CHECKS: {db_config.get('CONN_HEALTH_CHECKS')}")
print(f"OPTIONS: {db_config.get('OPTIONS', {})}")
EOF

# Check environment variables
kubectl exec -it deployment/soroscan-backend -n soroscan -- env | grep -E "DB_|DATABASE_"
```

### Check for Slow Queries

```bash
# Find slow queries consuming connections
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell <<EOF
SELECT 
  pid,
  now() - query_start as duration,
  state,
  query
FROM pg_stat_activity 
WHERE state = 'active'
  AND now() - query_start > interval '10 seconds'
ORDER BY duration DESC
LIMIT 10;
EOF
```

## Remediation Actions

### Option 1: Kill Idle Connections (Immediate Relief)

```bash
# Kill idle in transaction connections > 5 minutes
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity 
WHERE state = 'idle in transaction'
  AND now() - state_change > interval '5 minutes'
  AND pid != pg_backend_pid();
EOF

# Verify connections freed
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
```

**When to use**: Idle transactions detected, immediate relief needed  
**Risk**: Low - only kills idle transactions

### Option 2: Restart Application Pods (Clear All Connections)

```bash
# Restart backend pods (rolling restart)
kubectl rollout restart deployment/soroscan-backend -n soroscan

# Monitor restart
kubectl rollout status deployment/soroscan-backend -n soroscan

# Verify connections reset
sleep 30
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
```

**When to use**: Connection leaks suspected, need clean slate  
**Risk**: Medium - brief service interruption during rolling restart

### Option 3: Increase Database Max Connections (Temporary)

```bash
# For RDS/managed database
aws rds modify-db-parameter-group \
  --db-parameter-group-name soroscan-postgres \
  --parameters "ParameterName=max_connections,ParameterValue=200,ApplyMethod=immediate"

# For self-hosted PostgreSQL
kubectl exec -it postgres-0 -n soroscan -- psql -U postgres -c "ALTER SYSTEM SET max_connections = 200;"
kubectl exec -it postgres-0 -n soroscan -- psql -U postgres -c "SELECT pg_reload_conf();"
```

**When to use**: Legitimate high load, need more capacity  
**Risk**: Medium - may require database restart, check memory limits

### Option 4: Reduce Connection Pool Size Per Pod

```bash
# Reduce CONN_MAX_AGE to force connection recycling
kubectl set env deployment/soroscan-backend -n soroscan \
  CONN_MAX_AGE=300 \
  DB_POOL_SIZE=10

# Restart to apply
kubectl rollout restart deployment/soroscan-backend -n soroscan
```

**When to use**: Too many pods, each holding too many connections  
**Risk**: Low - may slightly increase connection overhead

### Option 5: Scale Down Pods (Emergency)

```bash
# Temporarily reduce backend replicas
CURRENT=$(kubectl get deployment soroscan-backend -n soroscan -o jsonpath='{.spec.replicas}')
NEW=$((CURRENT / 2))
kubectl scale deployment soroscan-backend -n soroscan --replicas=$NEW

# Monitor connection count
watch -n 5 'kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"'
```

**When to use**: Emergency, need to free connections immediately  
**Risk**: High - reduces capacity, only use if other options fail

### Option 6: Enable Connection Pooler (PgBouncer)

For long-term solution, deploy PgBouncer:

```yaml
# k8s/pgbouncer-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
  namespace: soroscan
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pgbouncer
  template:
    metadata:
      labels:
        app: pgbouncer
    spec:
      containers:
      - name: pgbouncer
        image: pgbouncer/pgbouncer:1.21
        ports:
        - containerPort: 5432
        env:
        - name: DATABASES_HOST
          value: "postgres.soroscan.svc.cluster.local"
        - name: DATABASES_PORT
          value: "5432"
        - name: DATABASES_DBNAME
          value: "soroscan"
        - name: PGBOUNCER_POOL_MODE
          value: "transaction"
        - name: PGBOUNCER_MAX_CLIENT_CONN
          value: "1000"
        - name: PGBOUNCER_DEFAULT_POOL_SIZE
          value: "25"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

**When to use**: Recurring issue, need connection pooling  
**Risk**: Low - but requires configuration change

## Automated Remediation

### Auto-Kill Idle Connections Script

```bash
#!/bin/bash
# scripts/auto-kill-idle-connections.sh

NAMESPACE="soroscan"
IDLE_THRESHOLD=300  # 5 minutes

kubectl exec -it deployment/soroscan-backend -n $NAMESPACE -- python manage.py dbshell <<EOF
DO \$\$
DECLARE
  killed_count INTEGER;
BEGIN
  SELECT count(*) INTO killed_count
  FROM pg_stat_activity 
  WHERE state = 'idle in transaction'
    AND now() - state_change > interval '$IDLE_THRESHOLD seconds'
    AND pid != pg_backend_pid();
  
  IF killed_count > 0 THEN
    PERFORM pg_terminate_backend(pid)
    FROM pg_stat_activity 
    WHERE state = 'idle in transaction'
      AND now() - state_change > interval '$IDLE_THRESHOLD seconds'
      AND pid != pg_backend_pid();
    
    RAISE NOTICE 'Killed % idle connections', killed_count;
  END IF;
END \$\$;
EOF
```

### Prometheus Alert Rules

```yaml
groups:
  - name: database_alerts
    interval: 30s
    rules:
      - alert: DatabaseConnectionPoolNearLimit
        expr: |
          (
            sum(pg_stat_activity_count{state!="idle"})
            /
            pg_settings_max_connections
          ) > 0.80
        for: 5m
        labels:
          severity: high
          component: database
        annotations:
          summary: "Database connection pool near limit"
          description: "Database connections at {{ $value | humanizePercentage }} of max (threshold: 80%)"
          runbook: "https://docs.soroscan.io/incident-response/db-connection-pool-exhausted"
      
      - alert: DatabaseConnectionPoolExhausted
        expr: |
          (
            sum(pg_stat_activity_count{state!="idle"})
            /
            pg_settings_max_connections
          ) > 0.95
        for: 1m
        labels:
          severity: critical
          component: database
        annotations:
          summary: "Database connection pool exhausted"
          description: "Database connections at {{ $value | humanizePercentage }} of max (threshold: 95%)"
          runbook: "https://docs.soroscan.io/incident-response/db-connection-pool-exhausted"
      
      - alert: DatabaseIdleInTransactionHigh
        expr: pg_stat_activity_count{state="idle in transaction"} > 10
        for: 5m
        labels:
          severity: medium
          component: database
        annotations:
          summary: "High number of idle in transaction connections"
          description: "{{ $value }} connections are idle in transaction (threshold: 10)"
          runbook: "https://docs.soroscan.io/incident-response/db-connection-pool-exhausted"
```

### CronJob for Periodic Cleanup

```yaml
# k8s/db-connection-cleanup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: db-connection-cleanup
  namespace: soroscan
spec:
  schedule: "*/5 * * * *"  # Every 5 minutes
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: soroscan-backend:latest
            command:
            - /bin/bash
            - -c
            - |
              python manage.py dbshell <<EOF
              SELECT pg_terminate_backend(pid)
              FROM pg_stat_activity 
              WHERE state = 'idle in transaction'
                AND now() - state_change > interval '5 minutes'
                AND pid != pg_backend_pid();
              EOF
          restartPolicy: OnFailure
```

## Verification Steps

After remediation:

```bash
# 1. Check connection count
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell <<EOF
SELECT 
  count(*) as total,
  count(*) FILTER (WHERE state = 'active') as active,
  count(*) FILTER (WHERE state = 'idle') as idle
FROM pg_stat_activity 
WHERE datname = current_database();
EOF

# 2. Check API error rate
kubectl logs -n soroscan -l app=soroscan-backend --tail=100 --since=5m | grep -c "500"

# 3. Verify no idle transactions
kubectl exec -it deployment/soroscan-backend -n soroscan -- python manage.py dbshell -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction';"

# 4. Test API endpoint
curl -s -o /dev/null -w "%{http_code}" http://soroscan-backend/api/health/
```

**Success Criteria**:
- Connections < 70% of max
- No 500 errors in logs
- No idle transactions > 1 minute
- API responding normally

## Communication Template

### Initial Alert

```
🚨 INCIDENT: Database Connection Issues

Status: Investigating
Impact: API errors, slow response times
Started: [timestamp]

We're experiencing database connection pool exhaustion.
Some API requests may fail or be slow.

Updates: Every 10 minutes
```

### Resolution

```
✅ RESOLVED: Database Connection Issues

Status: Resolved
Duration: X minutes
Root Cause: [brief description]

Database connections have returned to normal levels.
API is responding normally.

Actions taken:
- [list actions]

Prevention:
- [list prevention measures]
```

## Prevention

- **Monitoring**: Configure connection pool alerts at 80% and 95%
- **Connection Pooling**: Deploy PgBouncer for connection pooling
- **Idle Connection Cleanup**: Automated cleanup of idle transactions
- **Connection Limits**: Set appropriate CONN_MAX_AGE and pool sizes
- **Code Review**: Review code for connection leaks (unclosed cursors, transactions)
- **Load Testing**: Test connection pool under load
- **Database Sizing**: Ensure database has adequate max_connections for workload

## Related Playbooks

- [Event Ingestion Lag](./event-ingestion-lag.md) - May be caused by connection issues
- [RPC Endpoint Unavailable](./rpc-endpoint-unavailable.md) - Can increase connection usage

## Post-Incident Tasks

- [ ] Document root cause (connection leak, high load, etc.)
- [ ] Review application code for connection leaks
- [ ] Adjust connection pool configuration
- [ ] Consider deploying PgBouncer
- [ ] Update database sizing if needed
- [ ] Schedule post-mortem
- [ ] Update monitoring thresholds

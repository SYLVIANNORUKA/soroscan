#!/bin/bash
# Auto-remediation script for database connection pool issues
# Triggered by Prometheus alert: DatabaseConnectionPoolNearLimit

set -e

NAMESPACE="${NAMESPACE:-soroscan}"
IDLE_THRESHOLD_SECONDS="${IDLE_THRESHOLD_SECONDS:-300}"  # 5 minutes
CONNECTION_THRESHOLD_PERCENT="${CONNECTION_THRESHOLD_PERCENT:-80}"

echo "[$(date)] Starting auto-remediation for database connection pool..."

# Function to kill idle connections
kill_idle_connections() {
    kubectl exec -it deployment/soroscan-backend -n "$NAMESPACE" -- python manage.py dbshell <<EOF
DO \$\$
DECLARE
  killed_count INTEGER;
BEGIN
  -- Kill idle in transaction connections
  SELECT count(*) INTO killed_count
  FROM pg_stat_activity 
  WHERE state = 'idle in transaction'
    AND now() - state_change > interval '$IDLE_THRESHOLD_SECONDS seconds'
    AND pid != pg_backend_pid();
  
  IF killed_count > 0 THEN
    PERFORM pg_terminate_backend(pid)
    FROM pg_stat_activity 
    WHERE state = 'idle in transaction'
      AND now() - state_change > interval '$IDLE_THRESHOLD_SECONDS seconds'
      AND pid != pg_backend_pid();
    
    RAISE NOTICE 'Killed % idle in transaction connections', killed_count;
  END IF;
  
  -- Also kill very old idle connections (> 30 minutes)
  SELECT count(*) INTO killed_count
  FROM pg_stat_activity 
  WHERE state = 'idle'
    AND now() - state_change > interval '1800 seconds'
    AND pid != pg_backend_pid();
  
  IF killed_count > 0 THEN
    PERFORM pg_terminate_backend(pid)
    FROM pg_stat_activity 
    WHERE state = 'idle'
      AND now() - state_change > interval '1800 seconds'
      AND pid != pg_backend_pid();
    
    RAISE NOTICE 'Killed % old idle connections', killed_count;
  END IF;
END \$\$;
EOF
}

# Function to get connection stats
get_connection_stats() {
    kubectl exec -it deployment/soroscan-backend -n "$NAMESPACE" -- python manage.py dbshell <<EOF
SELECT 
  (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) as current_connections,
  (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections,
  (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction') as idle_in_transaction;
EOF
}

echo "[$(date)] Checking connection pool status..."
CONNECTION_STATS=$(get_connection_stats)
echo "[$(date)] Connection stats: $CONNECTION_STATS"

# Parse connection stats
CURRENT_CONNECTIONS=$(echo "$CONNECTION_STATS" | grep -oP '\d+' | sed -n '1p')
MAX_CONNECTIONS=$(echo "$CONNECTION_STATS" | grep -oP '\d+' | sed -n '2p')
IDLE_IN_TRANSACTION=$(echo "$CONNECTION_STATS" | grep -oP '\d+' | sed -n '3p')

if [ -z "$CURRENT_CONNECTIONS" ] || [ -z "$MAX_CONNECTIONS" ]; then
    echo "[$(date)] ERROR: Could not retrieve connection stats"
    exit 1
fi

CONNECTION_PERCENT=$((CURRENT_CONNECTIONS * 100 / MAX_CONNECTIONS))
echo "[$(date)] Connection usage: $CURRENT_CONNECTIONS/$MAX_CONNECTIONS ($CONNECTION_PERCENT%)"
echo "[$(date)] Idle in transaction: $IDLE_IN_TRANSACTION"

# Take action if threshold exceeded
if [ "$CONNECTION_PERCENT" -ge "$CONNECTION_THRESHOLD_PERCENT" ] || [ "$IDLE_IN_TRANSACTION" -gt 10 ]; then
    echo "[$(date)] Connection threshold exceeded or too many idle transactions. Cleaning up..."
    
    kill_idle_connections
    
    # Wait a moment and check again
    sleep 5
    NEW_STATS=$(get_connection_stats)
    NEW_CONNECTIONS=$(echo "$NEW_STATS" | grep -oP '\d+' | sed -n '1p')
    
    echo "[$(date)] Connections after cleanup: $NEW_CONNECTIONS/$MAX_CONNECTIONS"
    
    # Send notification
    # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"Auto-cleaned database connections: $CURRENT_CONNECTIONS → $NEW_CONNECTIONS (max: $MAX_CONNECTIONS)\"}"
    
    # If still high, consider restarting pods
    NEW_PERCENT=$((NEW_CONNECTIONS * 100 / MAX_CONNECTIONS))
    if [ "$NEW_PERCENT" -ge 90 ]; then
        echo "[$(date)] WARNING: Connections still high after cleanup. Consider manual intervention."
        # curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"⚠️ ALERT: Database connections still high ($NEW_PERCENT%) after cleanup. Manual intervention may be needed.\"}"
        exit 1
    fi
    
    exit 0
else
    echo "[$(date)] Connection usage within acceptable range. No action needed."
    exit 0
fi

---
id: incident-response/overview
title: Incident Response Overview
description: Overview of incident response procedures and playbooks for SoroScan
sidebar_label: Overview
hide_title: false
---

# Incident Response Overview

This directory contains incident response playbooks for common production issues in SoroScan.

## Quick Reference

| Incident Type | Severity | Playbook | Auto-Remediation |
|---------------|----------|----------|------------------|
| Event Ingestion Lag | High | [Event Ingestion Lag](./event-ingestion-lag.md) | Partial |
| Webhook Delivery Failure Burst | Medium | [Webhook Failures](./webhook-delivery-failures.md) | Yes |
| Database Connection Pool Exhausted | Critical | [DB Connection Pool](./db-connection-pool-exhausted.md) | Partial |
| RPC Endpoint Unavailable | High | [RPC Endpoint Down](./rpc-endpoint-unavailable.md) | Yes |

## Incident Severity Levels

- **Critical**: Service down or major functionality unavailable
- **High**: Significant degradation affecting multiple users
- **Medium**: Partial degradation or isolated issues
- **Low**: Minor issues with workarounds available

## General Incident Response Process

1. **Detect**: Alert fires or user reports issue
2. **Assess**: Determine severity and impact
3. **Respond**: Execute appropriate playbook
4. **Communicate**: Update status page and stakeholders
5. **Resolve**: Implement fix and verify
6. **Document**: Post-incident review and update playbooks

## Alert → Action Mapping

### Prometheus Alerts

| Alert Name | Severity | Playbook |
|------------|----------|----------|
| `EventIngestionLagHigh` | High | [Event Ingestion Lag](./event-ingestion-lag.md) |
| `WebhookFailureRateHigh` | Medium | [Webhook Failures](./webhook-delivery-failures.md) |
| `DatabaseConnectionPoolNearLimit` | High | [DB Connection Pool](./db-connection-pool-exhausted.md) |
| `DatabaseConnectionPoolExhausted` | Critical | [DB Connection Pool](./db-connection-pool-exhausted.md) |
| `RPCEndpointDown` | High | [RPC Endpoint Down](./rpc-endpoint-unavailable.md) |
| `CeleryQueueBacklog` | Medium | [Event Ingestion Lag](./event-ingestion-lag.md) |

## On-Call Contacts

- **Primary**: PagerDuty rotation
- **Escalation**: Engineering lead
- **Database Issues**: DBA team
- **Infrastructure**: DevOps team

## Tools & Access

- **Monitoring**: Grafana dashboards at `/grafana`
- **Logs**: Loki/ELK at `/logs`
- **Kubernetes**: `kubectl` access to `soroscan` namespace
- **Database**: Read-only access for diagnostics
- **Status Page**: Update at `status.soroscan.io`

## Post-Incident Checklist

After resolving any incident:

- [ ] Update status page to "Resolved"
- [ ] Document timeline in incident tracker
- [ ] Identify root cause
- [ ] Create follow-up tasks for prevention
- [ ] Update playbook if needed
- [ ] Schedule post-mortem (for Critical/High severity)
- [ ] Communicate resolution to affected users

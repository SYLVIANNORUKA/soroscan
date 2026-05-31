# Incident Response Template

Use this template to document incidents for post-mortem analysis.

## Incident Information

**Incident ID**: INC-YYYY-MM-DD-XXX  
**Date/Time Started**: YYYY-MM-DD HH:MM UTC  
**Date/Time Resolved**: YYYY-MM-DD HH:MM UTC  
**Duration**: X hours Y minutes  
**Severity**: Critical / High / Medium / Low  
**Status**: Investigating / Mitigated / Resolved  

## Summary

Brief description of the incident (1-2 sentences).

## Impact

- **Users Affected**: Number or percentage
- **Services Affected**: List of affected services
- **Data Loss**: Yes/No - describe if yes
- **Revenue Impact**: Estimated if applicable

## Timeline

| Time (UTC) | Event | Action Taken | By Whom |
|------------|-------|--------------|---------|
| HH:MM | Alert fired: EventIngestionLagHigh | | System |
| HH:MM | On-call engineer paged | | PagerDuty |
| HH:MM | Investigation started | Checked worker logs | Engineer Name |
| HH:MM | Root cause identified | Database connection pool exhausted | Engineer Name |
| HH:MM | Mitigation applied | Killed idle connections, scaled workers | Engineer Name |
| HH:MM | Service restored | Verified ingestion resumed | Engineer Name |
| HH:MM | Incident resolved | All metrics normal | Engineer Name |

## Root Cause

Detailed explanation of what caused the incident.

### Contributing Factors

- Factor 1
- Factor 2
- Factor 3

## Detection

- **How was it detected?**: Alert / User report / Monitoring
- **Alert that fired**: Alert name
- **Time to detect**: X minutes from start
- **Could detection be improved?**: Yes/No - explain

## Response

### Actions Taken

1. Action 1 - Result
2. Action 2 - Result
3. Action 3 - Result

### What Worked Well

- Item 1
- Item 2

### What Didn't Work Well

- Item 1
- Item 2

### Automation Used

- [ ] Auto-remediation script executed
- [ ] Manual intervention required
- [ ] Playbook followed: [Playbook Name](link)

## Resolution

Describe how the incident was resolved.

### Verification Steps

- [ ] Service health checks passing
- [ ] Metrics returned to normal
- [ ] No errors in logs
- [ ] User-facing functionality verified

## Prevention

### Immediate Actions (Complete within 24 hours)

- [ ] Action 1 - Owner - Due Date
- [ ] Action 2 - Owner - Due Date

### Short-term Actions (Complete within 1 week)

- [ ] Action 1 - Owner - Due Date
- [ ] Action 2 - Owner - Due Date

### Long-term Actions (Complete within 1 month)

- [ ] Action 1 - Owner - Due Date
- [ ] Action 2 - Owner - Due Date

## Lessons Learned

### What We Learned

1. Learning 1
2. Learning 2

### Process Improvements

1. Improvement 1
2. Improvement 2

### Documentation Updates

- [ ] Update playbook: [Playbook Name](link)
- [ ] Update runbook: [Runbook Name](link)
- [ ] Update monitoring: Alert thresholds, dashboards
- [ ] Update architecture docs

## Communication

### Internal Communication

- Slack channel: #incidents
- Status updates frequency: Every X minutes
- Stakeholders notified: List

### External Communication

- Status page updated: Yes/No
- Customer notification sent: Yes/No
- Social media update: Yes/No

### Communication Timeline

| Time (UTC) | Channel | Message |
|------------|---------|---------|
| HH:MM | Status Page | Investigating issue with event ingestion |
| HH:MM | Slack | Update: Root cause identified |
| HH:MM | Status Page | Issue resolved |

## Metrics

- **MTTD** (Mean Time To Detect): X minutes
- **MTTI** (Mean Time To Investigate): X minutes
- **MTTM** (Mean Time To Mitigate): X minutes
- **MTTR** (Mean Time To Resolve): X minutes

## Related Incidents

- [INC-YYYY-MM-DD-XXX](link) - Similar issue on different date
- [INC-YYYY-MM-DD-XXX](link) - Related component failure

## Attachments

- Grafana dashboard screenshots
- Log excerpts
- Database query results
- Slack conversation exports

---

**Post-Mortem Meeting**

- **Date**: YYYY-MM-DD
- **Attendees**: List of attendees
- **Recording**: Link to recording
- **Notes**: Link to meeting notes

# Dependency Triage Dashboard — Schema & UI Specification

## Design System

### Color Palette
- **Background:** `#FAFAFA` (stark white) or `#F5F5F5` (off-white)
- **Typography:** `#2D2D2D` (crisp charcoal) — all routine text
- **Accent (HIGH volatility only):** `#FFEB3B` (soft banana-yellow) — sparingly applied to row backgrounds
- **Border/Divider:** `#E0E0E0`
- **Success:** `#4CAF50`
- **Warning:** `#FF9800`
- **Critical:** `#F44336`

### Typography
- **Font:** Inter or system sans-serif
- **Routine logs:** 14px, weight 400, charcoal `#2D2D2D`
- **HIGH-volatility rows:** 14px, weight 500, background `#FFEB3B` at 20% opacity
- **Headers:** 16px, weight 600

---

## Table Schema: `Dependencies`

| Column | Type | Description |
|--------|------|-------------|
| `pr_number` | Number | GitHub PR number |
| `package_name` | Text | Package identifier |
| `ecosystem` | Single Select | `python`, `node`, `github-actions`, `docker` |
| `is_security` | Checkbox | Security-flagged by Dependabot |
| `volatility` | Single Select | `LOW`, `MEDIUM`, `HIGH` |
| `status` | Single Select | `eligible`, `quarantined`, `convergence_frozen` |
| `url` | URL | Link to PR |
| `updated_at` | DateTime | Last state projection timestamp |

### View: High-Risk Focus
- Filter: `volatility = HIGH OR status = convergence_frozen`
- Sort: `updated_at DESC`
- Row styling: `#FFEB3B` background at 20% opacity for `volatility = HIGH`

### View: Routine Queue
- Filter: `volatility = LOW AND status = quarantined`
- Sort: `quarantine_remaining_days ASC`

---

## Table Schema: `Vulnerability Events`

| Column | Type | Description |
|--------|------|-------------|
| `pr_number` | Number | GitHub PR number |
| `package_name` | Text | Affected package |
| `detected_at` | DateTime | When vulnerability was detected |
| `volatility` | Single Select | `LOW`, `MEDIUM`, `HIGH` |
| `requires_sandbox` | Checkbox | `true` if HIGH volatility + security |
| `resolved_at` | DateTime | When PR was merged or closed |

---

## Table Schema: `Quarantine Timers`

| Column | Type | Description |
|--------|------|-------------|
| `pr_number` | Number | GitHub PR number |
| `package_name` | Text | Package identifier |
| `created_days_ago` | Number | Days since PR was opened |
| `remaining_days` | Number | Days until quarantine clears |
| `eligible` | Checkbox | `true` if quarantine has cleared |

### View: Imminent Releases
- Filter: `remaining_days <= 3 AND eligible = false`
- Sort: `remaining_days ASC`

---

## Table Schema: `Convergence Events`

| Column | Type | Description |
|--------|------|-------------|
| `trigger_pr` | Number | PR that triggered convergence freeze |
| `ecosystem_a` | Text | First ecosystem |
| `ecosystem_b` | Text | Second ecosystem |
| `risk_multiplier` | Number | Convergence multiplier (2x, 3x, etc.) |
| `effective_risk` | Single Select | `HIGH`, `CRITICAL` |
| `frozen_at` | DateTime | When deployments were frozen |
| `resolved_at` | DateTime | When integration test passed |

---

## Webhook Payload Schema (v3.0)

```json
{
  "event_type": "dependency_audit",
  "timestamp": "2026-09-07T12:00:00Z",
  "schema_version": "3.0",
  "dependencies_table": [
    {
      "pr_number": 42,
      "package_name": "fastapi",
      "ecosystem": "python",
      "is_security": true,
      "volatility": "HIGH",
      "status": "quarantined",
      "url": "https://github.com/org/repo/pull/42"
    }
  ],
  "vulnerability_events_table": [
    {
      "pr_number": 42,
      "package_name": "fastapi",
      "detected_at": "2026-09-07T12:00:00Z",
      "volatility": "HIGH",
      "requires_sandbox": true
    }
  ],
  "quarantine_timers_table": [
    {
      "pr_number": 42,
      "package_name": "fastapi",
      "created_days_ago": 3,
      "remaining_days": 11,
      "eligible": false
    }
  ],
  "metrics": {
    "total_dependencies": 1,
    "vulnerability_events": 1,
    "quarantined": 1,
    "eligible_for_merge": 0,
    "high_risk_blocked": 1
  }
}
```

### Receipt Response (Required)
The webhook endpoint must return HTTP 200 with a JSON body containing a row identifier:
```json
{
  "id": "rec1234567890",
  "success": true
}
```

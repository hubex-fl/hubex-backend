# HUBEX Pricing Model

*Last updated: 2026-03-28*

---

## Overview

HUBEX follows an **Open Core** pricing model. The core platform is free and open-source. Premium features, extended limits, and professional support are available through paid tiers.

All tiers can be self-hosted. Cloud-hosted options will be available in the future.

---

## Tier Comparison

| Feature | Free (Open Source) | Pro ($29/month per org) | Enterprise (Custom) |
|---|---|---|---|
| **Devices** | Up to 5 | Up to 50 | Unlimited |
| **Organizations** | 1 | 3 | Unlimited |
| **Users per org** | 3 | 10 | Unlimited |
| **Variable history** | 7 days | 90 days | 1 year+ (configurable) |
| **Automation rules** | 5 | Unlimited | Unlimited |
| **Telemetry retention** | 7 days | 90 days | Custom |
| | | | |
| **Core features** | | | |
| Device management | Yes | Yes | Yes |
| Pairing (QR + API) | Yes | Yes | Yes |
| Variable streams | Yes | Yes | Yes |
| Dashboard | Yes | Yes | Yes |
| OTA updates | Yes | Yes | Yes |
| REST API (150+ endpoints) | Yes | Yes | Yes |
| Webhooks | 3 subscriptions | Unlimited | Unlimited |
| Events + Audit log | Yes | Yes | Yes |
| | | | |
| **Pro features** | | | |
| Geofence automations | -- | Yes | Yes |
| n8n integration templates | -- | Yes | Yes |
| Email notifications | -- | Yes | Yes |
| Priority support | -- | Yes | Yes |
| Custom variable categories | -- | Yes | Yes |
| Advanced OTA strategies | Basic (immediate) | Staged + Canary | Staged + Canary + Custom |
| | | | |
| **Enterprise features** | | | |
| SSO / SAML integration | -- | -- | Yes |
| White-label option | -- | -- | Yes |
| Custom deployment | -- | -- | Yes (on-prem, air-gapped) |
| Dedicated support + SLA | -- | -- | Yes (99.9% uptime) |
| API rate limit customization | Default | Default | Custom |
| Backup automation | Manual | Scheduled (daily) | Custom schedule + S3 |
| Audit log export | -- | -- | Yes (CSV, JSON, SIEM) |

---

## Tier Details

### Free (Open Source)

The Free tier includes the complete HUBEX platform with all core features. No credit card required. Self-hosted only.

**Included:**
- 5 devices, 1 organization, 3 users
- Full device lifecycle (pair, telemetry, variables, OTA)
- 5 automation rules (variable threshold, device offline)
- 3 webhook subscriptions
- 7-day variable history and telemetry retention
- Mission Control dashboard with variable streams
- REST API access (standard rate limits)
- Community support (GitHub Issues, Discussions)
- Docker Compose deployment

**Best for:** Hobbyists, makers, proof-of-concept projects, evaluating HUBEX.

---

### Pro ($29/month per organization)

Everything in Free, plus extended limits and professional features. Self-hosted or future cloud-hosted.

**Added in Pro:**
- 50 devices, 3 organizations, 10 users per org
- Unlimited automation rules including geofence triggers
- Unlimited webhook subscriptions
- 90-day variable history and telemetry retention
- n8n integration templates (pre-built workflows)
- Email notification actions in automations
- Staged + canary OTA rollout strategies
- Custom variable categories
- Priority support (48-hour response time)
- Scheduled daily backups

**Best for:** IoT startups, small teams, product development, pilot deployments.

---

### Enterprise (Custom Pricing)

Everything in Pro, plus unlimited scale, enterprise security, and dedicated support.

**Added in Enterprise:**
- Unlimited devices, organizations, and users
- 1-year+ configurable variable history
- SSO/SAML integration (Azure AD, Okta, Google Workspace)
- White-label option (custom branding, domain)
- Custom deployment options (on-premises, air-gapped, Kubernetes)
- Dedicated support engineer + SLA (99.9% uptime guarantee)
- Custom API rate limits
- Audit log export (CSV, JSON, SIEM integration)
- Custom backup schedule + S3/cloud storage
- Early access to new features (MCP, Agent SDK, Dashboard Builder)
- Training and onboarding sessions

**Best for:** Enterprises, system integrators, hardware manufacturers, managed service providers.

---

## Frequently Asked Questions

### Can I self-host the Pro or Enterprise tier?

**Yes.** All tiers support self-hosting. You receive a license key that unlocks Pro or Enterprise features in your self-hosted instance. No cloud dependency.

### Can I switch tiers at any time?

**Yes.** Upgrade or downgrade at any time. When downgrading, existing data beyond the new tier's limits is preserved but becomes read-only until you reduce usage or upgrade again.

### What happens when I exceed device limits?

You receive a warning at 80% capacity. At 100%, new device pairing is blocked but existing devices continue to operate normally. No data loss, no service interruption.

### Is there a free trial for Pro?

**Yes.** 14-day free trial of Pro features, no credit card required. Automatically reverts to Free tier after the trial.

### Do you offer discounts for startups or education?

**Yes.** 50% discount on Pro for verified startups (< 2 years, < $1M revenue) and educational institutions. Contact us for details.

### What about annual billing?

Annual billing saves 20%: Pro at $278/year instead of $348/year ($23.17/month effective).

### Is the source code really open?

**Yes.** The core platform is MIT-licensed. Pro and Enterprise features are source-available with a commercial license. You can read, audit, and modify the code.

---

## Build vs. Buy: ROI Calculation

### The Cost of Building Your Own IoT Backend

| Component | Engineering Time | Cost (at $100/hr) |
|---|---|---|
| Device authentication + pairing | 2 weeks | $8,000 |
| Telemetry ingestion + storage | 2 weeks | $8,000 |
| Variable/state management | 1 week | $4,000 |
| Dashboard + visualization | 3 weeks | $12,000 |
| Alerting + notifications | 1 week | $4,000 |
| OTA update system | 2 weeks | $8,000 |
| Multi-tenancy + RBAC | 2 weeks | $8,000 |
| API documentation | 1 week | $4,000 |
| Testing + deployment | 2 weeks | $8,000 |
| **Total** | **16 weeks (4 months)** | **$64,000** |

### The Cost of Using HUBEX

| | Free | Pro | Enterprise |
|---|---|---|---|
| License cost (year 1) | $0 | $348 | Custom |
| Setup time | 1 hour | 1 hour | 2 hours + onboarding |
| Maintenance | Community self-serve | Priority support | Dedicated engineer |
| **Total year 1** | **$0** | **$348** | **~$5,000-15,000** |

### Savings

| Metric | Build from scratch | Use HUBEX (Pro) | Savings |
|---|---|---|---|
| Time to first device | 4-6 months | 1 hour | 4-6 months |
| Engineering cost | $64,000+ | $348/year | $63,652+ |
| Ongoing maintenance | 1 FTE ($120K/yr) | Included | $120K/year |
| Risk (security, bugs) | High (custom code) | Low (battle-tested) | Significant |

> **Bottom line:** HUBEX saves $50,000+ in upfront engineering costs and 4-6 months of development time. The Pro tier pays for itself in the first day.

---

## Add-On Pricing (Future)

| Add-On | Price | Description |
|---|---|---|
| Extra device pack (+25) | $10/month | For Pro tier; add devices beyond the 50 limit |
| Extended history (365 days) | $15/month | For Pro tier; extend from 90 to 365 days |
| Dedicated MQTT broker | $20/month | Managed MQTT broker with HUBEX integration |
| White-label branding | $50/month | Custom logo, colors, domain (Pro tier) |
| Premium support | $99/month | 4-hour response SLA (Pro tier upgrade) |

---

## Contact

- **Sales:** sales@hubex.io
- **Support:** support@hubex.io
- **GitHub:** github.com/hubex-iot/hubex
- **Demo:** Request a live demo at demo.hubex.io

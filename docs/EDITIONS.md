# HubEx Editions: Community vs Enterprise

## Philosophie

**Community Edition** = Kein Maker/Hobbyist soll je das Gefühl haben, eingeschränkt zu sein.
Keine künstlichen Limits bei Devices, Variables, Dashboards, oder Automations.

**Enterprise Edition** = Features die man braucht wenn man damit Geld verdient oder
ein Unternehmen betreibt. White-Label, Multi-Tenant, erweiterte Security, Priority Support.

## Feature-Matrix

### Core Platform (Community = Enterprise)

| Feature | Community | Enterprise |
|---------|-----------|-----------|
| Devices (alle 4 Typen) | Unbegrenzt | Unbegrenzt |
| Variables + Semantic Types (20+) | Unbegrenzt | Unbegrenzt |
| Dashboards + alle Widget-Typen | Unbegrenzt | Unbegrenzt |
| Dashboard Builder (Add/Edit/Layout) | Voll | Voll |
| Automation Rules (7 Trigger + 7 Actions) | Unbegrenzt | Unbegrenzt |
| AND/OR Bedingungsgruppen | Ja | Ja |
| Alerts + Alert Rules | Unbegrenzt | Unbegrenzt |
| Computed Variables + Snapshots | Ja | Ja |
| Webhooks | Unbegrenzt | Unbegrenzt |
| REST API + OpenAPI Docs | Voll | Voll |
| Events + Audit Log | Ja (90 Tage) | Ja (unbegrenzt) |
| Export/Import (JSON) | Ja | Ja |
| Dark/Light Mode | Ja | Ja |
| i18n (DE + EN) | Ja | Ja |
| Device Wizard (4 Flows) | Ja | Ja |
| System Health Dashboard | Ja | Ja |
| Board Profiles + Pin Map | Ja | Ja |
| Component Library (15+ Bausteine) | Ja | Ja |
| PWA (installierbar auf Mobile) | Ja | Ja |

### User & Organization (Limit in Community)

| Feature | Community | Enterprise |
|---------|-----------|-----------|
| Organisationen | 1 | Unbegrenzt |
| User pro Organisation | 5 (Owner + 4) | Unbegrenzt |
| Rollen | Owner, Operator, Viewer | + Admin, Kiosk, Custom Roles |
| 2FA/MFA (TOTP) | Ja | Ja + WebAuthn |
| Session Management | Ja | Ja |
| API Keys (Scoped) | 3 | Unbegrenzt |

### Enterprise-Only Features

| Feature | Community | Enterprise |
|---------|-----------|-----------|
| White-Label Branding (Logo, Name, Farben) | "Powered by [Produkt]" | Vollständig |
| Kiosk-Modus | Nein | Ja |
| Public Dashboard Embed | Basis (Token) | + PIN, Custom Domain |
| Multi-Tenant (Mandanten-Hierarchie) | Nein | Ja |
| Tenant Nodes (Kunde → Gebäude → Einheit) | Nein | Ja |
| Custom API Builder | Nein | Ja |
| Email Template Editor | Nein | Ja |
| Report Generator (HTML/PDF) | Nein | Ja |
| Scheduled Reports + Email-Versand | Nein | Ja |
| Plugin Framework (Install + Execute) | Nein | Ja |
| Flow Editor (visuell) | Nein | Ja |
| Hardware Code Generator | Nein | Ja |
| Bridge Protocol (ESP → Arduino) | Nein | Ja |
| Retrofit Device Profiles (Modbus, CAN) | Nein | Ja |
| Trace Timeline + Anomaly Detection | Basis | Erweitert |
| Admin Console (Module Management) | Nein | Ja |
| Priority Support + SLA | Nein | Ja |
| Redis Scaling (Queue, Cache, Pub/Sub) | Nein | Ja |
| Variable History Partitioning | Nein | Ja |

## Lizenz-Enforcement

### Technische Umsetzung: Signed License File

```
Community: Keine License-Datei nötig → voller Community-Feature-Set
Enterprise: license.json im Config-Verzeichnis → Enterprise-Features freigeschaltet
```

**License-Datei Struktur:**
```json
{
  "licensee": "Firma GmbH",
  "plan": "enterprise",
  "max_users": 0,
  "max_orgs": 0,
  "features": ["white_label", "multi_tenant", "custom_api", "plugins", ...],
  "issued_at": "2026-04-01T00:00:00Z",
  "expires_at": "2027-04-01T00:00:00Z",
  "signature": "Ed25519-Signatur..."
}
```

**Validierung:**
- Backend liest `license.json` beim Start
- Prüft Ed25519-Signatur gegen eingebetteten Public Key
- Ohne gültige Lizenz → Community-Modus (kein Crash, keine Fehlermeldung)
- Feature-Flags werden aus License in den JWT Token eingebettet
- Frontend prüft Feature-Flags und blendet Enterprise-UI aus/ein

**Warum nicht einfach umgehbar:**
- Signatur-Prüfung mit Public Key (Private Key nur bei uns)
- Selbst wenn jemand den Code ändert: er muss den Signatur-Check
  UND die Feature-Flag-Prüfung an dutzenden Stellen entfernen
- AGPL-Lizenz erfordert Offenlegung von Änderungen → rechtlich geschützt

## Preisstruktur (Entwurf)

| Plan | Preis | Zielgruppe |
|------|-------|------------|
| Community (Self-Hosted) | Kostenlos, forever | Maker, Hobbyisten, Studenten |
| Enterprise Self-Hosted | ~79/Monat oder 790/Jahr | KMU, Dienstleister |
| Enterprise Managed | ~299/Monat | Unternehmen ohne DevOps |
| Custom/On-Premise | Auf Anfrage | Enterprise mit Sonderanforderungen |

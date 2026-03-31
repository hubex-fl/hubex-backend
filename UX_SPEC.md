# UX GESAMTSPEZIFIKATION — DEFINITIVE REFERENZ

Dieses Dokument wurde aus den User-Prompts (prompt.txt bis prompt 6.txt) konsolidiert.
Es ist die EINZIGE UX-Referenz. Alle vorherigen UX-Dokumente sind damit ersetzt.

Siehe die Originaldateien auf dem Desktop des Users:
- C:\Users\lange\Desktop\prompt.txt (Problembericht + Grundprinzipien)
- C:\Users\lange\Desktop\prompt1.txt (Observability, Settings, allgemeine Kritik)
- C:\Users\lange\Desktop\prompt2.txt (UX Flow Spec: Grundprinzipien, Design System, Navigation)
- C:\Users\lange\Desktop\prompt3.txt (Globale Features, First-Login, Add Device Wizard, Devices, Device-Detail ANFANG)
- C:\Users\lange\Desktop\prompt 4.txt (Device-Detail KOMPLETT, Entities, Variablen)
- C:\Users\lange\Desktop\prompt 5.txt (Dashboard Builder, Automations, Alerts, Observability, Settings, API Docs, System Health)
- C:\Users\lange\Desktop\prompt 6.txt (Connect-Panel, Auto-Discovery, Demo-Datensatz, Durchgängige Anforderungen, Priorisierung)

## Prioritäten für die nächste Session:

### PRIO 1 — Sofort sichtbare UX-Änderungen:
1. Sidebar: Gruppen nach Spec (HAUPT/DATEN/SYSTEM), default ZU
2. Kontextuelles Weiterleiten: "Create Alert"/"Create Automation" von Variable → Builder MIT Kontext
3. DeviceDetail: Name inline editierbar, doppelte Offline-Anzeige weg, Task/Signal bei Offline verstecken
4. Automations: Kompakte Cards (nur Name + Zusammenfassung + Status)
5. Variablen: Gruppierung nach Device, Device-Links
6. Tooltips auf alle unklaren Icons (weißer Kreis, Uhr, Priority, Secrets, Cooldown)
7. Empty States mit CTAs auf JEDER leeren Seite

### PRIO 2 — Größere Features:
1. Add Device Wizard (4 Flows: Hardware, Service, Bridge, Agent)
2. System Context / Platinen-Ansicht mit klickbaren Elementen
3. Automations: Visueller If→Then Builder
4. Connect-Panel Inline-Formulare

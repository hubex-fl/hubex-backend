#!/usr/bin/env python3
"""HUBEX Demo Presenter — automated walkthrough using MCP tools.

Logs into HUBEX and executes a timed sequence of MCP tool calls to
demonstrate all major features.  The user just starts screen recording
and runs this script.

Usage:
    python scripts/demo-presenter.py --help
    python scripts/demo-presenter.py
    python scripts/demo-presenter.py --speed fast --start-from 3
    python scripts/demo-presenter.py --sequence teaser
    python scripts/demo-presenter.py --server http://192.168.1.5:8000

Requires: requests (pip install requests)
"""

import argparse
import json
import sys
import time
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required.  Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Demo sequences
# ---------------------------------------------------------------------------

# Each step has:
#   delay   — seconds to wait BEFORE this action (scaled by --speed)
#   action  — MCP tool action type
#   ...     — action-specific arguments

FULL_SEQUENCE: list[dict[str, Any]] = [
    # ── Act 1: Welcome (12s) ────────────────────────────────────────────
    {"act": 1, "label": "Welcome", "delay": 1, "action": "navigate", "path": "/"},
    {"delay": 2, "action": "camera", "camera_action": "zoom_to", "selector": ".kpi-card, .kpi-card:first-child", "zoom": 1.8, "duration": 1000},
    {"delay": 2, "action": "highlight", "selector": ".kpi-card:first-child", "message": "Echtzeit-Ueberblick: Devices, Alerts, Events", "duration": 4},
    {"delay": 4, "action": "camera", "camera_action": "reset", "duration": 600},

    # ── Act 2: Devices (15s) ────────────────────────────────────────────
    {"act": 2, "label": "Devices", "delay": 2, "action": "navigate", "path": "/devices"},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "Alle Geraete an einem Ort - Hardware, APIs, Bridges, Agents", "duration": 4},
    {"delay": 5, "action": "navigate", "path": "/devices/1"},
    {"delay": 2, "action": "camera", "camera_action": "zoom_to", "selector": ".hero-card, .device-hero", "zoom": 1.5, "duration": 800},
    {"delay": 3, "action": "highlight", "selector": ".hero-card, .device-hero", "message": "Live-Status, Variablen, History - alles auf einen Blick", "duration": 4},
    {"delay": 4, "action": "camera", "camera_action": "reset"},

    # ── Act 3: System Map (15s) ─────────────────────────────────────────
    {"act": 3, "label": "System Map", "delay": 2, "action": "navigate", "path": "/flow-editor"},
    {"delay": 2, "action": "highlight", "selector": ".flow-canvas, canvas, svg", "message": "Systemkarte: Wie alles vernetzt ist", "duration": 4},
    {"delay": 5, "action": "fly_to_node", "node_id": "device-1"},
    {"delay": 3, "action": "camera", "camera_action": "zoom_to", "selector": ".inspector-panel", "zoom": 1.8, "duration": 800},
    {"delay": 3, "action": "camera", "camera_action": "reset"},

    # ── Act 4: Dashboard (15s) ──────────────────────────────────────────
    {"act": 4, "label": "Dashboard", "delay": 2, "action": "navigate", "path": "/dashboards/8"},
    {"delay": 2, "action": "camera", "camera_action": "zoom_to", "selector": ".viz-widget:first-child", "zoom": 2.0, "duration": 1000},
    {"delay": 3, "action": "highlight", "selector": ".viz-widget:first-child", "message": "Live Charts, Gauges, Custom HTML - alles konfigurierbar", "duration": 4},
    {"delay": 4, "action": "camera", "camera_action": "reset"},

    # ── Act 5: Sandbox (10s) ────────────────────────────────────────────
    {"act": 5, "label": "Sandbox", "delay": 2, "action": "navigate", "path": "/sandbox"},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "Sandbox: Virtuelle Geraete simulieren", "duration": 4},

    # ── Act 6: MCP (10s) ────────────────────────────────────────────────
    {"act": 6, "label": "MCP / AI Coop", "delay": 5, "action": "navigate", "path": "/mcp"},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "MCP Server: KI steuert HubEx direkt", "duration": 4},

    # ── Finale (8s) ─────────────────────────────────────────────────────
    {"act": 7, "label": "Finale", "delay": 5, "action": "navigate", "path": "/"},
    {"delay": 2, "action": "camera", "camera_action": "zoom_to", "selector": ".getting-started, h1", "zoom": 1.3, "duration": 1200},
    {"delay": 3, "action": "highlight", "selector": "h1, .page-title", "message": "HubEx - Anbinden. Verstehen. Visualisieren. Automatisieren.", "duration": 6},
    {"delay": 6, "action": "camera", "camera_action": "reset"},
]

SHORT_SEQUENCE: list[dict[str, Any]] = [
    # Condensed ~40 second version with camera
    {"act": 1, "label": "Welcome", "delay": 1, "action": "navigate", "path": "/"},
    {"delay": 2, "action": "camera", "camera_action": "zoom_to", "selector": ".kpi-card, .kpi-card:first-child", "zoom": 1.5, "duration": 800},
    {"delay": 2, "action": "highlight", "selector": ".kpi-card:first-child", "message": "Echtzeit-Ueberblick ueber alle Geraete", "duration": 3},
    {"delay": 3, "action": "camera", "camera_action": "reset", "duration": 500},

    {"act": 2, "label": "Devices", "delay": 2, "action": "navigate", "path": "/devices"},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "Hardware, APIs, Bridges, Agents - ein Ort", "duration": 3},

    {"act": 3, "label": "System Map", "delay": 3, "action": "navigate", "path": "/flow-editor"},
    {"delay": 2, "action": "fly_to_node", "node_id": "device-1"},
    {"delay": 2, "action": "highlight", "selector": ".flow-canvas, canvas, svg", "message": "Systemkarte - alles vernetzt", "duration": 3},

    {"act": 4, "label": "Dashboards", "delay": 3, "action": "navigate", "path": "/dashboards"},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "Custom Dashboards mit Live-Daten", "duration": 3},

    {"act": 5, "label": "AI Coop", "delay": 3, "action": "navigate", "path": "/mcp"},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "KI-Integration via MCP", "duration": 3},

    {"act": 6, "label": "Finale", "delay": 3, "action": "navigate", "path": "/"},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "HubEx - Anbinden. Verstehen. Visualisieren. Automatisieren.", "duration": 4},
]

TEASER_SEQUENCE: list[dict[str, Any]] = [
    # Ultra-short ~15 second teaser with camera
    {"act": 1, "label": "Dashboard", "delay": 1, "action": "navigate", "path": "/"},
    {"delay": 2, "action": "camera", "camera_action": "zoom_to", "selector": ".kpi-card, h1", "zoom": 1.5, "duration": 800},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "HubEx - der universelle IoT Device Hub", "duration": 3},
    {"delay": 3, "action": "camera", "camera_action": "reset", "duration": 500},

    {"act": 2, "label": "System Map", "delay": 1, "action": "navigate", "path": "/flow-editor"},
    {"delay": 2, "action": "fly_to_node", "node_id": "device-1"},

    {"act": 3, "label": "Finale", "delay": 3, "action": "navigate", "path": "/"},
    {"delay": 2, "action": "highlight", "selector": "h1, .page-title", "message": "Anbinden. Verstehen. Visualisieren. Automatisieren.", "duration": 3},
]

SEQUENCES = {
    "full": FULL_SEQUENCE,
    "short": SHORT_SEQUENCE,
    "teaser": TEASER_SEQUENCE,
}

SPEED_MULTIPLIERS = {
    "slow": 2.0,
    "normal": 1.0,
    "fast": 0.5,
}


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class HubexClient:
    """Simple HTTP client for the HUBEX MCP endpoints."""

    def __init__(self, server: str, email: str, password: str, verbose: bool = False):
        self.server = server.rstrip("/")
        self.email = email
        self.password = password
        self.verbose = verbose
        self.token: str | None = None
        self.session = requests.Session()

    def log(self, msg: str) -> None:
        print(f"  {msg}", flush=True)

    def debug(self, msg: str) -> None:
        if self.verbose:
            print(f"  [debug] {msg}", file=sys.stderr, flush=True)

    def login(self) -> bool:
        """Authenticate and store the JWT token."""
        try:
            r = self.session.post(
                f"{self.server}/api/v1/auth/login",
                json={"email": self.email, "password": self.password},
                timeout=10,
            )
            r.raise_for_status()
            self.token = r.json()["access_token"]
            self.debug(f"Logged in as {self.email}")
            return True
        except Exception as e:
            print(f"  ERROR: Login failed: {e}", file=sys.stderr)
            return False

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool via the REST endpoint."""
        self.debug(f"Calling {tool_name}({json.dumps(arguments, ensure_ascii=False)[:120]})")
        try:
            r = self.session.post(
                f"{self.server}/api/v1/mcp/tools/call",
                headers=self._headers(),
                json={"name": tool_name, "arguments": arguments},
                timeout=30,
            )
            r.raise_for_status()
            result = r.json()
            is_error = result.get("isError", False)
            if is_error:
                self.debug(f"  Tool returned error: {result}")
            return result
        except Exception as e:
            self.log(f"ERROR calling {tool_name}: {e}")
            return {"isError": True, "content": [{"type": "text", "text": str(e)}]}


# ---------------------------------------------------------------------------
# Action executors
# ---------------------------------------------------------------------------

def execute_step(client: HubexClient, step: dict[str, Any]) -> dict[str, Any] | None:
    """Execute a single demo step and return the MCP result (if any)."""
    action = step["action"]

    if action == "navigate":
        return client.call_tool("hubex_navigate", {"path": step["path"]})

    elif action == "notification":
        return client.call_tool("hubex_show_notification", {
            "message": step["message"],
            "type": step.get("type", "info"),
        })

    elif action == "highlight":
        return client.call_tool("hubex_highlight_element", {
            "selector": step["selector"],
            "message": step.get("message", ""),
            "duration": step.get("duration", 3),
        })

    elif action == "camera":
        return client.call_tool("hubex_camera", {
            "action": step.get("camera_action", "reset"),
            "selector": step.get("selector", ""),
            "zoom": step.get("zoom", 2.0),
            "duration": step.get("duration", 800),
            "x": step.get("x", 0),
            "y": step.get("y", 0),
        })

    elif action == "fly_to_node":
        return client.call_tool("hubex_fly_to_node", {"node_id": step["node_id"]})

    elif action == "start_tour":
        return client.call_tool("hubex_start_tour", {"tour_id": step["tour_id"]})

    elif action == "create_automation":
        return client.call_tool("hubex_create_automation", {
            "name": step["name"],
            "trigger_type": step["trigger_type"],
            "trigger_config": step.get("trigger_config", {}),
            "action_type": step["action_type"],
            "action_config": step.get("action_config", {}),
            "enabled": step.get("enabled", True),
        })

    elif action == "create_dashboard":
        return client.call_tool("hubex_create_dashboard", {
            "name": step["name"],
            "widgets": step.get("widgets", []),
        })

    elif action == "create_device":
        return client.call_tool("hubex_create_device", {
            "name": step["name"],
            "device_type": step.get("device_type", "hardware"),
        })

    else:
        client.log(f"Unknown action: {action}")
        return None


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_demo(
    client: HubexClient,
    sequence: list[dict[str, Any]],
    speed_mult: float = 1.0,
    start_from: int = 1,
) -> None:
    """Run a demo sequence with timed delays."""
    total_steps = len(sequence)
    current_act = 0
    skipping = True

    print()
    print("=" * 60)
    print("  HUBEX Demo Presenter")
    print("=" * 60)
    print()

    # Calculate estimated duration
    raw_duration = sum(s.get("delay", 0) for s in sequence)
    est_duration = raw_duration * speed_mult
    print(f"  Sequence: {total_steps} steps")
    print(f"  Estimated duration: ~{int(est_duration)}s (speed: x{1/speed_mult:.1f})")
    print(f"  Starting from act: {start_from}")
    print()
    print("-" * 60)

    for i, step in enumerate(sequence, 1):
        # Track acts for --start-from
        if "act" in step:
            current_act = step["act"]
            if current_act >= start_from:
                skipping = False

        if skipping:
            continue

        # Print act headers
        if "act" in step and "label" in step:
            print()
            print(f"  --- Act {step['act']}: {step['label']} ---")

        # Wait
        delay = step.get("delay", 0) * speed_mult
        if delay > 0:
            print(f"  [{i}/{total_steps}] Waiting {delay:.1f}s ...", end="", flush=True)
            time.sleep(delay)
            print(" OK")

        # Execute
        action_label = step["action"]
        detail = ""
        if action_label == "navigate":
            detail = step["path"]
        elif action_label == "notification":
            detail = step["message"][:50]
        elif action_label == "highlight":
            detail = step["selector"][:40]
        elif action_label == "camera":
            detail = f"{step.get('camera_action', 'reset')} {step.get('selector', '')[:30]}"
        elif action_label == "fly_to_node":
            detail = step["node_id"]
        elif action_label == "create_automation":
            detail = step["name"]
        elif action_label == "create_dashboard":
            detail = step["name"]

        print(f"  [{i}/{total_steps}] {action_label}: {detail}", end="", flush=True)
        result = execute_step(client, step)

        if result and result.get("isError"):
            print(f" [ERROR]")
        else:
            print(f" [OK]")

    print()
    print("-" * 60)
    print("  Demo complete!")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="HUBEX Demo Presenter — automated feature walkthrough via MCP tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Sequences:
  full    ~90s complete walkthrough of all features (default)
  short   ~30s condensed version with key highlights
  teaser  ~15s ultra-short teaser: Dashboard, System Map, done

Speed:
  slow     x0.5 speed (double delays) — for detailed narration
  normal   x1.0 speed (default)
  fast     x2.0 speed (halved delays) — quick preview

Examples:
  %(prog)s                                   # full demo, normal speed
  %(prog)s --sequence teaser --speed fast     # quick 8-second teaser
  %(prog)s --start-from 4                     # skip to Act 4 (Automations)
  %(prog)s --server http://192.168.1.5:8000   # remote HUBEX server
""",
    )
    parser.add_argument(
        "--server", default="http://localhost:8000",
        help="HUBEX backend URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--email", default="test@test.com",
        help="Login email (default: test@test.com)",
    )
    parser.add_argument(
        "--password", default="Test1234!",
        help="Login password (default: Test1234!)",
    )
    parser.add_argument(
        "--sequence", choices=["full", "short", "teaser"], default="full",
        help="Demo sequence to run (default: full)",
    )
    parser.add_argument(
        "--speed", choices=["slow", "normal", "fast"], default="normal",
        help="Playback speed (default: normal)",
    )
    parser.add_argument(
        "--start-from", type=int, default=1, dest="start_from",
        help="Skip to this act number (default: 1)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show debug output for API calls",
    )
    parser.add_argument(
        "--list-sequences", action="store_true", dest="list_sequences",
        help="List all available sequences with their steps and exit",
    )

    args = parser.parse_args()

    if args.list_sequences:
        for name, seq in SEQUENCES.items():
            raw_dur = sum(s.get("delay", 0) for s in seq)
            acts = sorted({s["act"] for s in seq if "act" in s})
            print(f"\n  {name.upper()} (~{int(raw_dur)}s, {len(seq)} steps, {len(acts)} acts)")
            for s in seq:
                if "act" in s and "label" in s:
                    print(f"    Act {s['act']}: {s['label']}")
        print()
        return

    # Connect
    client = HubexClient(
        server=args.server,
        email=args.email,
        password=args.password,
        verbose=args.verbose,
    )

    print(f"\n  Connecting to {args.server} ...")
    if not client.login():
        print("  FATAL: Could not authenticate. Check credentials and server availability.")
        sys.exit(1)
    print(f"  Authenticated as {args.email}")

    # Run
    sequence = SEQUENCES[args.sequence]
    speed_mult = SPEED_MULTIPLIERS[args.speed]
    run_demo(client, sequence, speed_mult, args.start_from)


if __name__ == "__main__":
    main()

"""Built-in plugin catalog — hardcoded list of ship-with plugins.

Sprint 3 shipped the first three (n8n + Anthropic Claude + OpenAI).
Sprint 6 adds three more service plugins that extend the same Portainer
runtime infrastructure:

* **n8n** — service plugin, workflow automation (adopted from compose)
* **anthropic-claude** — connector plugin, Anthropic API credentials
* **openai** — connector plugin, OpenAI-compatible API credentials
* **frigate** — service plugin, NVR + camera ML (iframe-capable)
* **ollama** — service plugin, local LLM runtime (headless, pair with OpenAI connector)
* **grafana** — service plugin, embedded dashboards (iframe via GF_SECURITY_ALLOW_EMBEDDING)

Catalog entries are pure data. Decisions that depend on runtime state (e.g.
"does the n8n container already exist on this host?") live in the install
handler, not here. The handler uses ``adopt_container_name`` to decide
whether to adopt an existing container instead of spawning a fresh one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PluginKind = Literal["service", "connector"]


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One ship-with plugin definition.

    ``manifest`` is the dict written to ``Plugin.manifest`` on install.
    Its shape depends on ``kind`` (see plan: service vs connector schema).
    """

    key: str
    name: str
    description: str
    kind: PluginKind
    category: str
    manifest: dict[str, Any]
    icon_url: str | None = None
    docs_url: str | None = None
    # Service plugins only: if a container with this name already exists on
    # the Docker host, the install handler "adopts" it instead of spawning a
    # fresh one. Used for n8n which is already part of docker-compose.full.yml.
    adopt_container_name: str | None = None
    # Freeform tags for the marketplace UI (e.g. "ai", "workflow").
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_public_dict(self) -> dict[str, Any]:
        """JSON-ready dict for the HTTP catalog endpoint."""
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "category": self.category,
            "manifest": self.manifest,
            "icon_url": self.icon_url,
            "docs_url": self.docs_url,
            "adopt_container_name": self.adopt_container_name,
            "tags": list(self.tags),
        }


# ---------------------------------------------------------------------------
# Ship-with catalog entries
# ---------------------------------------------------------------------------

_N8N_MANIFEST: dict[str, Any] = {
    "kind": "service",
    "docker": {
        "image": "n8nio/n8n:latest",
        "container_name": "hubex-plugin-n8n",
        "ports": [{"host": 5678, "container": 5678}],
        "env": [
            {"key": "N8N_BASIC_AUTH_ACTIVE", "value": "false"},
            {"key": "GENERIC_TIMEZONE", "value": "Europe/Berlin"},
            {"key": "WEBHOOK_URL", "value": "http://localhost:5678/"},
        ],
        "volumes": [
            {"source": "hubex_plugin_n8n", "target": "/home/node/.n8n"}
        ],
    },
    "embed": {
        # n8n is a full-fledged app designed to run fullscreen with its own
        # navigation, user profile, and websocket connections. It sets
        # X-Frame-Options: sameorigin + Cross-Origin-Resource-Policy:
        # same-origin + uses absolute asset paths (/static/, /assets/,
        # /rest/) that would need deep sub_filter rewriting to work inside
        # a reverse-proxied iframe. Rather than fight the framework with
        # brittle path rewriting, we open n8n in a new tab. The container
        # is still managed by hubex (adopted), credentials/workflows stay
        # in the n8n volume, status still visible in the Plugins list.
        "allow_iframe": False,
        "iframe_url": "http://localhost:5678",
        "open_url": "http://localhost:5678",
        # proxy_path is unused for n8n but kept so the infrastructure is
        # exercised in tests. Future service plugins that DO support
        # iframing (e.g. Grafana with GF_SECURITY_ALLOW_EMBEDDING=true)
        # will reuse the nginx /plugins-embed/ location without any
        # further config changes.
        "proxy_path": "/plugins-embed/n8n/",
        "sidebar_label": "n8n Workflows",
        "sidebar_icon": "workflow",
    },
    "health": {
        "endpoint": "http://localhost:5678/healthz",
        "expected_status": 200,
    },
}

_CLAUDE_MANIFEST: dict[str, Any] = {
    "kind": "connector",
    "category": "ai",
    "credential_schema": [
        {
            "key": "api_key",
            "label": "API Key",
            "type": "string",
            "secret": True,
            "required": True,
            "placeholder": "sk-ant-...",
        },
        {
            "key": "model",
            "label": "Default Model",
            "type": "select",
            "secret": False,
            "required": False,
            "options": [
                "claude-sonnet-4-5",
                "claude-opus-4-5",
                "claude-haiku-4-5",
            ],
            "default": "claude-sonnet-4-5",
        },
    ],
    "provides": ["ai.chat_completion", "ai.tool_use", "ai.vision"],
    "test_endpoint": {
        "url": "https://api.anthropic.com/v1/models",
        "method": "GET",
        "headers": {
            "x-api-key": "${api_key}",
            "anthropic-version": "2023-06-01",
        },
    },
}

_OPENAI_MANIFEST: dict[str, Any] = {
    "kind": "connector",
    "category": "ai",
    "credential_schema": [
        {
            "key": "api_key",
            "label": "API Key",
            "type": "string",
            "secret": True,
            "required": True,
            "placeholder": "sk-...",
        },
        {
            "key": "base_url",
            "label": "Base URL",
            "type": "string",
            "secret": False,
            "required": False,
            "default": "https://api.openai.com/v1",
            "help": "Change this to use OpenAI-compatible providers (Groq, Together, Ollama).",
        },
        {
            "key": "model",
            "label": "Default Model",
            "type": "select",
            "secret": False,
            "required": False,
            "options": ["gpt-4o", "gpt-4o-mini", "gpt-5", "gpt-5-mini"],
            "default": "gpt-4o",
        },
    ],
    "provides": ["ai.chat_completion", "ai.embeddings"],
    "test_endpoint": {
        "url": "${base_url}/models",
        "method": "GET",
        "headers": {"Authorization": "Bearer ${api_key}"},
    },
}


# ---------------------------------------------------------------------------
# Sprint 6 — additional service plugins
# ---------------------------------------------------------------------------

_FRIGATE_MANIFEST: dict[str, Any] = {
    "kind": "service",
    "docker": {
        # Frigate ships as a single image with the web UI + the Python
        # detection worker. We pin the -stable tag so installs are
        # reproducible between HubEx upgrades. Users can switch to a
        # specific version tag via a Sprint-future "edit manifest" UI.
        "image": "ghcr.io/blakeblackshear/frigate:stable",
        "container_name": "hubex-plugin-frigate",
        "ports": [
            {"host": 5000, "container": 5000},   # Web UI + API
            {"host": 8554, "container": 8554},   # RTSP restream
            {"host": 8555, "container": 8555},   # WebRTC
        ],
        "env": [
            # Frigate reads its main config from /config/config.yml; users
            # must populate that file with their cameras BEFORE first
            # start. We point the volume at a HubEx-managed path so the
            # config survives plugin restarts. A future sprint can expose
            # a Frigate-config editor via the Plugin configure modal.
            {"key": "TZ", "value": "Europe/Berlin"},
        ],
        "volumes": [
            {"source": "hubex_plugin_frigate_config", "target": "/config"},
            {"source": "hubex_plugin_frigate_media", "target": "/media/frigate"},
        ],
    },
    "embed": {
        # Frigate's web UI uses absolute asset paths but DOES honor the
        # X-Frame-Options when the backend is set to allow it. For v1 we
        # link out to a new tab (same compromise as n8n) — iframing a
        # live video UI is brittle anyway because MSE/WebRTC assumes the
        # top-level origin. Users get the management UI in a new tab,
        # HubEx still owns the container and health status.
        "allow_iframe": False,
        "iframe_url": "http://localhost:5000",
        "open_url": "http://localhost:5000",
        "proxy_path": "/plugins-embed/frigate/",
        "sidebar_label": "Frigate NVR",
        "sidebar_icon": "camera",
    },
    "health": {
        "endpoint": "http://localhost:5000/api/config",
        "expected_status": 200,
    },
}


_OLLAMA_MANIFEST: dict[str, Any] = {
    "kind": "service",
    "docker": {
        # Ollama is a headless LLM runtime — it exposes an OpenAI-compatible
        # HTTP API on port 11434 but has NO web UI. Users interact with it
        # via the existing HubEx "openai" connector plugin (just point
        # base_url at http://ollama:11434/v1). Pulling models is a CLI
        # operation (`docker exec hubex-plugin-ollama ollama pull llama3`)
        # for now — a future sprint can surface a "pull model" button in
        # the Plugin configure modal.
        "image": "ollama/ollama:latest",
        "container_name": "hubex-plugin-ollama",
        "ports": [{"host": 11434, "container": 11434}],
        "env": [
            # Keep models loaded in memory for a bit so consecutive
            # queries don't re-load from disk every time.
            {"key": "OLLAMA_KEEP_ALIVE", "value": "30m"},
        ],
        "volumes": [
            # Large volume for model storage (can easily be 10-50 GB).
            {"source": "hubex_plugin_ollama_models", "target": "/root/.ollama"},
        ],
    },
    "embed": {
        # Pure runtime — no UI to embed or open. "open_url" points to
        # the /api/tags endpoint which lists loaded models and is the
        # closest thing to a "is it working?" page.
        "allow_iframe": False,
        "iframe_url": None,
        "open_url": "http://localhost:11434/api/tags",
        "proxy_path": None,
        "sidebar_label": "Ollama",
        "sidebar_icon": "cpu",
    },
    "health": {
        # Ollama responds 200 on the root path with "Ollama is running".
        "endpoint": "http://localhost:11434/",
        "expected_status": 200,
    },
}


_GRAFANA_MANIFEST: dict[str, Any] = {
    "kind": "service",
    "docker": {
        "image": "grafana/grafana-oss:latest",
        "container_name": "hubex-plugin-grafana",
        "ports": [{"host": 3000, "container": 3000}],
        "env": [
            # Enable iframe embedding + anonymous viewer access so HubEx
            # dashboards can surface Grafana panels without a separate
            # login. Admins still need to sign in to Grafana to edit;
            # this only enables read-only embed views.
            {"key": "GF_SECURITY_ALLOW_EMBEDDING", "value": "true"},
            {"key": "GF_AUTH_ANONYMOUS_ENABLED", "value": "true"},
            {"key": "GF_AUTH_ANONYMOUS_ORG_ROLE", "value": "Viewer"},
            # Allow loading Grafana under any origin's iframe — HubEx
            # runs on localhost/domain so we need to relax the default
            # same-origin policy.
            {"key": "GF_SECURITY_COOKIE_SAMESITE", "value": "disabled"},
            {"key": "GF_SERVER_ROOT_URL", "value": "http://localhost:3000/"},
        ],
        "volumes": [
            {"source": "hubex_plugin_grafana_data", "target": "/var/lib/grafana"},
        ],
    },
    "embed": {
        # Grafana with GF_SECURITY_ALLOW_EMBEDDING=true is the cleanest
        # iframe experience of our three new service plugins — dashboards
        # render correctly inside HubEx. We still offer open_url for the
        # "edit" workflow which is better in a full browser tab.
        "allow_iframe": True,
        "iframe_url": "http://localhost:3000",
        "open_url": "http://localhost:3000",
        "proxy_path": "/plugins-embed/grafana/",
        "sidebar_label": "Grafana",
        "sidebar_icon": "chart",
    },
    "health": {
        "endpoint": "http://localhost:3000/api/health",
        "expected_status": 200,
    },
}


CATALOG: tuple[CatalogEntry, ...] = (
    CatalogEntry(
        key="n8n",
        name="n8n",
        description=(
            "Visual workflow automation. Connect HubEx devices to 400+ external "
            "services with a drag-and-drop editor. Embedded directly in HubEx."
        ),
        kind="service",
        category="automation",
        manifest=_N8N_MANIFEST,
        # Sprint 3.4 — inline icons so catalog cards have visual identity
        # without an extra HTTP round-trip or CDN dependency. Emoji are
        # used as a pragmatic v1; Sprint 3.5 can swap to SVG paths if the
        # design system settles on a monochrome icon set.
        icon_url="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>\U0001F300</text></svg>",
        docs_url="https://docs.n8n.io",
        adopt_container_name="hubex-n8n",
        tags=("workflow", "automation", "low-code"),
    ),
    CatalogEntry(
        key="anthropic-claude",
        name="Anthropic Claude",
        description=(
            "Claude AI models from Anthropic. Stores your API key in HubEx secrets "
            "so any part of HubEx (AI Coop, automation nodes, dashboards) can use it."
        ),
        kind="connector",
        category="ai",
        manifest=_CLAUDE_MANIFEST,
        icon_url="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>\U0001F9E0</text></svg>",
        docs_url="https://docs.anthropic.com",
        tags=("ai", "llm", "chat"),
    ),
    CatalogEntry(
        key="openai",
        name="OpenAI",
        description=(
            "OpenAI or any OpenAI-compatible API (GPT, Groq, Together, Ollama). "
            "Stores the API key and base URL in HubEx secrets for reuse across features."
        ),
        kind="connector",
        category="ai",
        manifest=_OPENAI_MANIFEST,
        icon_url="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>\U00002728</text></svg>",
        docs_url="https://platform.openai.com/docs",
        tags=("ai", "llm", "embeddings"),
    ),
    # Sprint 6 — additional service plugins extending the Portainer
    # runtime infrastructure built in Sprint 3.
    CatalogEntry(
        key="frigate",
        name="Frigate",
        description=(
            "Open-source NVR with real-time camera object detection. Connects "
            "your IP cameras, runs ML inference on a Coral TPU or CPU, and feeds "
            "detection events into HubEx automations. Management UI opens in a new tab."
        ),
        kind="service",
        category="surveillance",
        manifest=_FRIGATE_MANIFEST,
        icon_url="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>\U0001F4F9</text></svg>",
        docs_url="https://docs.frigate.video",
        tags=("video", "ml", "nvr", "cctv", "object-detection"),
    ),
    CatalogEntry(
        key="ollama",
        name="Ollama",
        description=(
            "Local LLM runtime — run open-source models (Llama, Mistral, Phi, "
            "Qwen, ...) on your own hardware with an OpenAI-compatible API. "
            "Pair with the OpenAI connector (base_url=http://ollama:11434/v1) "
            "to use your local models everywhere HubEx talks to an LLM."
        ),
        kind="service",
        category="ai",
        manifest=_OLLAMA_MANIFEST,
        icon_url="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>\U0001F999</text></svg>",
        docs_url="https://ollama.com/library",
        tags=("ai", "llm", "local", "self-hosted"),
    ),
    CatalogEntry(
        key="grafana",
        name="Grafana",
        description=(
            "Metric dashboards with rich visualisations. Point Grafana at the "
            "HubEx PostgreSQL or a Prometheus exporter, build panels, then embed "
            "them directly inside HubEx dashboards. Iframe-embeddable out of the box."
        ),
        kind="service",
        category="monitoring",
        manifest=_GRAFANA_MANIFEST,
        icon_url="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>\U0001F4C8</text></svg>",
        docs_url="https://grafana.com/docs/grafana/latest",
        tags=("monitoring", "dashboard", "metrics", "time-series"),
    ),
)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def list_catalog() -> list[CatalogEntry]:
    """Return all catalog entries (ordered as declared)."""
    return list(CATALOG)


def get_catalog_entry(key: str) -> CatalogEntry | None:
    """Lookup a catalog entry by its ``key``. ``None`` if not found."""
    for entry in CATALOG:
        if entry.key == key:
            return entry
    return None

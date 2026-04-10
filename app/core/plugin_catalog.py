"""Built-in plugin catalog — hardcoded list of ship-with plugins (Sprint 3).

v1 ships **three** plugins. They are defined inline as Python data so IDEs
can type-check the manifests and there is no I/O at startup. A future
sprint can replace this with a remote catalog fetch (out of scope for v1).

* **n8n** — service plugin, workflow automation embedded via iframe
* **anthropic-claude** — connector plugin, Anthropic API credentials
* **openai** — connector plugin, OpenAI-compatible API credentials

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
        "iframe_url": "http://localhost:5678",
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
        docs_url="https://platform.openai.com/docs",
        tags=("ai", "llm", "embeddings"),
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

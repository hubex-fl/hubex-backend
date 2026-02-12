from app.core.capabilities import CAPABILITY_REGISTRY
from app.db.base import Base
from app.db.models.providers import ProviderInstance, ProviderType


def test_provider_tables_registered():
    assert ProviderType.__tablename__ == "provider_types"
    assert ProviderInstance.__tablename__ == "provider_instances"
    assert "provider_types" in Base.metadata.tables
    assert "provider_instances" in Base.metadata.tables


def test_phase3_capability_placeholders_registered():
    assert "providers.read" in CAPABILITY_REGISTRY
    assert "providers.write" in CAPABILITY_REGISTRY
    assert "signals.read" in CAPABILITY_REGISTRY
    assert "signals.ingest" in CAPABILITY_REGISTRY

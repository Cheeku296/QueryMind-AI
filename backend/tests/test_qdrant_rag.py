import pytest
from app.ai.rag.qdrant_manager import qdrant_manager


def test_qdrant_health_and_stats():
    stats = qdrant_manager.get_stats()
    assert "error" not in stats
    assert stats["collection_name"] == qdrant_manager.collection_name


def test_qdrant_schema_retrieval():
    retrieved = qdrant_manager.retrieve_relevant_schema(
        workspace_id="00000000-0000-0000-0000-000000000001",
        connection_id="00000000-0000-0000-0000-000000000002",
        query="department employee salaries",
        limit=5,
    )
    assert "tables" in retrieved
    assert "compact_context" in retrieved
    assert len(retrieved["compact_context"]) > 0


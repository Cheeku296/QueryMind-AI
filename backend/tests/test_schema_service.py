import pytest
from app.models.connection import DatabaseConnection
from app.core.security import encrypt_secret
from app.services.schema_service import SchemaService


def test_schema_introspection_and_er_diagram():
    conn = DatabaseConnection(
        name="Demo Introspection Test",
        database_type="postgresql",
        host="localhost",
        port=5432,
        database_name="querymind_demo",
        username="postgres",
        encrypted_credentials=encrypt_secret("postgrespassword"),
    )

    result = SchemaService.introspect_connection(conn)
    assert result["total_tables"] >= 8
    table_names = [t["name"] for t in result["tables"]]
    for expected in ["employees", "departments", "customers", "products", "orders", "order_items", "payments", "subscriptions"]:
        assert expected in table_names

    er_data = SchemaService.generate_er_diagram_data(result)
    assert len(er_data["nodes"]) >= 8
    assert len(er_data["edges"]) >= 6

    preview = SchemaService.get_table_preview(conn, "departments", limit=5)
    assert len(preview["rows"]) > 0
    assert "name" in preview["columns"]

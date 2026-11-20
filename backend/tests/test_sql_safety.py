import pytest
from app.ai.sql_safety.validator import SQLValidator


def test_select_allowed_and_limit_enforced():
    """Verify standard SELECT is permitted and safe LIMIT is injected."""
    result = SQLValidator.validate_sql("SELECT id, name FROM employees")
    assert result.is_valid is True
    assert "LIMIT" in result.sanitized_sql
    assert "employees" in result.tables_used


def test_insert_rejected():
    """Verify INSERT statements are rejected."""
    result = SQLValidator.validate_sql("INSERT INTO employees (name) VALUES ('Hacker')")
    assert result.is_valid is False
    assert any("INSERT" in err for err in result.errors)


def test_update_rejected():
    """Verify UPDATE statements are rejected."""
    result = SQLValidator.validate_sql("UPDATE employees SET salary = 999999 WHERE id = 1")
    assert result.is_valid is False
    assert any("UPDATE" in err for err in result.errors)


def test_delete_rejected():
    """Verify DELETE statements are rejected."""
    result = SQLValidator.validate_sql("DELETE FROM employees WHERE id = 1")
    assert result.is_valid is False
    assert any("DELETE" in err for err in result.errors)


def test_drop_rejected():
    """Verify DROP TABLE statements are rejected."""
    result = SQLValidator.validate_sql("DROP TABLE customers CASCADE")
    assert result.is_valid is False
    assert any("DROP" in err for err in result.errors)


def test_alter_rejected():
    """Verify ALTER TABLE statements are rejected."""
    result = SQLValidator.validate_sql("ALTER TABLE employees ADD COLUMN ssn text")
    assert result.is_valid is False
    assert any("ALTER" in err for err in result.errors)


def test_multiple_statements_rejected():
    """Verify stacked multi-statements are rejected."""
    result = SQLValidator.validate_sql("SELECT id FROM orders; DROP TABLE orders;")
    assert result.is_valid is False
    assert any("Multiple" in err for err in result.errors)


def test_dangerous_function_rejected():
    """Verify dangerous system functions like pg_sleep are rejected."""
    result = SQLValidator.validate_sql("SELECT pg_sleep(10)")
    assert result.is_valid is False
    assert any("pg_sleep" in err for err in result.errors)


def test_complex_cte_and_joins_allowed():
    """Verify complex analytical queries with CTEs and aggregates are permitted."""
    sql = """
    WITH monthly_orders AS (
        SELECT customer_id, COUNT(id) as total_orders
        FROM orders
        GROUP BY customer_id
    )
    SELECT c.first_name, c.last_name, m.total_orders
    FROM customers c
    JOIN monthly_orders m ON m.customer_id = c.id
    ORDER BY m.total_orders DESC
    LIMIT 20;
    """
    result = SQLValidator.validate_sql(sql)
    assert result.is_valid is True
    assert "customers" in result.tables_used
    assert "orders" in result.tables_used


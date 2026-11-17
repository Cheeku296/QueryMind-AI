import logging
import re
from typing import Any, Dict, List, Optional, Set
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.core.config import settings

logger = logging.getLogger(__name__)

PROHIBITED_STATEMENTS = {
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Set,
    exp.Kill,
}

DANGEROUS_FUNCTIONS = {
    "pg_sleep",
    "dblink",
    "dblink_exec",
    "pg_read_file",
    "pg_write_file",
    "pg_read_binary_file",
    "query_to_xml",
    "system",
    "exec",
    "load_file",
    "into_outfile",
}


class SQLValidationResult:
    def __init__(
        self,
        is_valid: bool,
        sanitized_sql: str,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        tables_used: Optional[List[str]] = None,
        columns_used: Optional[List[str]] = None,
        has_limit: bool = False,
        statement_type: str = "SELECT",
    ):
        self.is_valid = is_valid
        self.sanitized_sql = sanitized_sql
        self.errors = errors or []
        self.warnings = warnings or []
        self.tables_used = tables_used or []
        self.columns_used = columns_used or []
        self.has_limit = has_limit
        self.statement_type = statement_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "sanitized_sql": self.sanitized_sql,
            "errors": self.errors,
            "warnings": self.warnings,
            "tables_used": self.tables_used,
            "columns_used": self.columns_used,
            "has_limit": self.has_limit,
            "statement_type": self.statement_type,
        }


class SQLValidator:
    """Deterministic SQLGlot-based security and dialect validator."""

    @classmethod
    def validate_sql(
        cls,
        sql: str,
        dialect: str = "postgres",
        allowed_tables: Optional[Set[str]] = None,
        max_rows: int = settings.SQL_MAX_ROWS_RETURNED,
    ) -> SQLValidationResult:
        if not sql or not sql.strip():
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql="",
                errors=["SQL statement is empty."],
            )

        clean_sql = sql.strip().rstrip(";")
        # Remove markdown code blocks if present
        clean_sql = re.sub(r"^```(?:sql)?\s*", "", clean_sql, flags=re.IGNORECASE)
        clean_sql = re.sub(r"\s*```$", "", clean_sql)
        clean_sql = clean_sql.strip()

        errors: List[str] = []
        warnings: List[str] = []

        # 1. Parse statement with SQLGlot
        try:
            parsed_expressions = sqlglot.parse(clean_sql, read=dialect)
        except ParseError as e:
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql=clean_sql,
                errors=[f"SQL Syntax Error: {str(e)}"],
            )
        except Exception as e:
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql=clean_sql,
                errors=[f"Failed to parse SQL: {str(e)}"],
            )

        if not parsed_expressions or parsed_expressions[0] is None:
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql=clean_sql,
                errors=["No executable SQL expression found."],
            )

        # 2. Reject multiple statements
        if len(parsed_expressions) > 1:
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql=clean_sql,
                errors=["Multiple SQL statements are strictly prohibited for security."],
            )

        expr = parsed_expressions[0]

        # 3. Check for prohibited DDL / DML operations
        for prohibited in PROHIBITED_STATEMENTS:
            if isinstance(expr, prohibited) or expr.find(prohibited):
                return SQLValidationResult(
                    is_valid=False,
                    sanitized_sql=clean_sql,
                    errors=[f"Prohibited SQL operation detected: {prohibited.__name__.upper()} is not allowed. Only read-only queries are permitted."],
                )

        # Ensure expression is a SELECT or CTE (exp.Select or exp.Union)
        if not (isinstance(expr, (exp.Select, exp.Union)) or expr.find(exp.Select)):
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql=clean_sql,
                errors=["Only SELECT queries and Common Table Expressions (WITH ...) are permitted."],
            )

        # 4. Check dangerous functions
        for func in expr.find_all(exp.Anonymous, exp.Func):
            func_name = func.name.lower() if hasattr(func, "name") else ""
            if func_name in DANGEROUS_FUNCTIONS:
                return SQLValidationResult(
                    is_valid=False,
                    sanitized_sql=clean_sql,
                    errors=[f"Dangerous or unauthorized SQL function '{func_name}()' is prohibited."],
                )

        # 5. Extract tables and columns used
        tables_found: Set[str] = set()
        for table in expr.find_all(exp.Table):
            t_name = table.name.lower()
            if t_name:
                tables_found.add(t_name)

        # Check allowed tables if provided
        if allowed_tables:
            normalized_allowed = {t.lower() for t in allowed_tables}
            for tbl in tables_found:
                if tbl not in normalized_allowed:
                    errors.append(f"Table '{tbl}' does not exist in the connected database schema.")

        columns_found: Set[str] = set()
        for col in expr.find_all(exp.Column):
            c_name = col.name.lower()
            if c_name:
                columns_found.add(c_name)

        if errors:
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql=clean_sql,
                errors=errors,
                tables_used=list(tables_found),
                columns_used=list(columns_found),
            )

        # 6. Enforce LIMIT
        has_limit = False
        limit_expr = expr.args.get("limit")
        if limit_expr:
            has_limit = True
            try:
                limit_val = int(limit_expr.expression.this)
                if limit_val > max_rows:
                    warnings.append(f"Requested LIMIT ({limit_val}) exceeds safety maximum ({max_rows}). Capped to {max_rows}.")
                    expr.args["limit"].expression.this = str(max_rows)
            except Exception:
                pass
        else:
            # Inject LIMIT
            expr = expr.limit(max_rows)
            warnings.append(f"No LIMIT specified. Automatically applied safety limit of {max_rows} rows.")

        # Re-generate sanitized SQL in postgres dialect
        sanitized_sql = expr.sql(dialect=dialect)

        return SQLValidationResult(
            is_valid=True,
            sanitized_sql=sanitized_sql,
            errors=[],
            warnings=warnings,
            tables_used=list(tables_found),
            columns_used=list(columns_found),
            has_limit=has_limit,
            statement_type="SELECT",
        )

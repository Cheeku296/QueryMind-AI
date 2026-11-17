import logging
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.models.connection import DatabaseConnection
from app.services.connection_service import ConnectionService

logger = logging.getLogger(__name__)


class SQLExecutionResult:
    def __init__(
        self,
        success: bool,
        columns: Optional[List[str]] = None,
        rows: Optional[List[List[Any]]] = None,
        row_count: int = 0,
        execution_time_ms: int = 0,
        error: Optional[str] = None,
        executed_sql: str = "",
    ):
        self.success = success
        self.columns = columns or []
        self.rows = rows or []
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.error = error
        self.executed_sql = executed_sql

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "executed_sql": self.executed_sql,
        }


class SQLExecutor:
    """Executes validated read-only SQL queries against target databases."""

    @classmethod
    def execute_query(
        cls,
        conn: DatabaseConnection,
        validated_sql: str,
        timeout_seconds: int = settings.SQL_QUERY_TIMEOUT_SECONDS,
        max_rows: int = settings.SQL_MAX_ROWS_RETURNED,
    ) -> SQLExecutionResult:
        if not validated_sql or not validated_sql.strip():
            return SQLExecutionResult(success=False, error="Empty SQL query.", executed_sql=validated_sql)

        url = ConnectionService.get_connection_url(conn)
        # Configure connection with timeout
        connect_args = {"connect_timeout": 5}
        engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)

        start_time = time.perf_counter()
        try:
            with engine.connect() as connection:
                # 1. Enforce read-only transaction and statement timeout in PostgreSQL
                if conn.database_type.lower() == "postgresql":
                    connection.execute(text(f"SET statement_timeout = '{timeout_seconds * 1000}';"))
                    connection.execute(text("SET TRANSACTION READ ONLY;"))

                # 2. Execute validated query
                cursor = connection.execute(text(validated_sql))
                columns = list(cursor.keys())
                raw_rows = cursor.fetchmany(max_rows)

                # Format rows (convert non-serializable objects)
                clean_rows = []
                for row in raw_rows:
                    clean_row = []
                    for val in row:
                        if val is None:
                            clean_row.append(None)
                        elif isinstance(val, (int, float, bool, str)):
                            clean_row.append(val)
                        else:
                            clean_row.append(str(val))
                    clean_rows.append(clean_row)

                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return SQLExecutionResult(
                    success=True,
                    columns=columns,
                    rows=clean_rows,
                    row_count=len(clean_rows),
                    execution_time_ms=duration_ms,
                    executed_sql=validated_sql,
                )

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            err_msg = str(e)
            logger.warning(f"SQL execution failed ({duration_ms}ms): {err_msg}")
            # Sanitize error message to avoid exposing raw connection credentials
            if conn.username in err_msg:
                err_msg = err_msg.replace(conn.username, "***")
            return SQLExecutionResult(
                success=False,
                error=err_msg,
                execution_time_ms=duration_ms,
                executed_sql=validated_sql,
            )
        finally:
            engine.dispose()

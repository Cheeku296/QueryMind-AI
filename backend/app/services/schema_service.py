import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.connection import DatabaseConnection, SchemaSnapshot
from app.services.connection_service import ConnectionService

logger = logging.getLogger(__name__)


class SchemaService:
    @classmethod
    def introspect_connection(cls, conn: DatabaseConnection) -> Dict[str, Any]:
        """Performs comprehensive schema introspection on an external database."""
        if conn.database_type.lower() == "postgresql":
            return cls._introspect_postgresql(conn)
        elif conn.database_type.lower() == "mysql":
            return cls._introspect_mysql(conn)
        else:
            raise NotImplementedError(f"Introspection for '{conn.database_type}' not yet implemented.")

    @classmethod
    def _introspect_postgresql(cls, conn: DatabaseConnection) -> Dict[str, Any]:
        url = ConnectionService.get_connection_url(conn)
        engine = create_engine(url, pool_pre_ping=True)

        tables_meta: Dict[str, Dict[str, Any]] = {}
        relationships: List[Dict[str, Any]] = []

        try:
            with engine.connect() as connection:
                # 1. Fetch tables and views in public schema
                tables_query = text("""
                    SELECT 
                        t.table_name,
                        t.table_type,
                        coalesce(c.reltuples::bigint, 0) as row_count,
                        obj_description(c.oid, 'pg_class') as table_comment
                    FROM information_schema.tables t
                    JOIN pg_class c ON c.relname = t.table_name
                    JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
                    WHERE t.table_schema = 'public'
                    ORDER BY t.table_name;
                """)
                for row in connection.execute(tables_query):
                    tbl_name = row[0]
                    tbl_type = row[1]
                    row_cnt = max(0, int(row[2]))
                    comment = row[3] or ""

                    tables_meta[tbl_name] = {
                        "name": tbl_name,
                        "schema": "public",
                        "type": "table" if "TABLE" in tbl_type else "view",
                        "row_count": row_cnt,
                        "description": comment,
                        "columns": [],
                        "primary_key": [],
                        "foreign_keys": [],
                        "indexes": [],
                        "unique_constraints": [],
                    }

                # 2. Fetch columns
                cols_query = text("""
                    SELECT 
                        c.table_name,
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        col_description((c.table_schema || '.' || c.table_name)::regclass::oid, c.ordinal_position) as col_comment
                    FROM information_schema.columns c
                    WHERE c.table_schema = 'public'
                    ORDER BY c.table_name, c.ordinal_position;
                """)
                for row in connection.execute(cols_query):
                    tbl_name = row[0]
                    if tbl_name in tables_meta:
                        col_info = {
                            "name": row[1],
                            "data_type": row[2],
                            "is_nullable": (row[3] == "YES"),
                            "default_value": row[4],
                            "description": row[5] or "",
                        }
                        tables_meta[tbl_name]["columns"].append(col_info)

                # 3. Fetch primary keys
                pk_query = text("""
                    SELECT
                        tc.table_name, 
                        kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND tc.table_schema = 'public'
                    ORDER BY tc.table_name, kcu.ordinal_position;
                """)
                for row in connection.execute(pk_query):
                    tbl_name, col_name = row[0], row[1]
                    if tbl_name in tables_meta:
                        tables_meta[tbl_name]["primary_key"].append(col_name)

                # 4. Fetch foreign keys & relationships
                fk_query = text("""
                    SELECT
                        tc.table_name AS source_table,
                        kcu.column_name AS source_column,
                        ccu.table_name AS target_table,
                        ccu.column_name AS target_column,
                        tc.constraint_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public';
                """)
                for row in connection.execute(fk_query):
                    src_tbl, src_col, tgt_tbl, tgt_col, constraint_name = row[0], row[1], row[2], row[3], row[4]
                    if src_tbl in tables_meta:
                        fk_entry = {
                            "column": src_col,
                            "target_table": tgt_tbl,
                            "target_column": tgt_col,
                            "constraint_name": constraint_name,
                        }
                        tables_meta[src_tbl]["foreign_keys"].append(fk_entry)

                    rel_entry = {
                        "source_table": src_tbl,
                        "source_column": src_col,
                        "target_table": tgt_tbl,
                        "target_column": tgt_col,
                        "relationship_type": "many-to-one",
                    }
                    relationships.append(rel_entry)

                # 5. Fetch indexes
                idx_query = text("""
                    SELECT
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname;
                """)
                for row in connection.execute(idx_query):
                    tbl_name, idx_name, idx_def = row[0], row[1], row[2]
                    if tbl_name in tables_meta:
                        tables_meta[tbl_name]["indexes"].append({
                            "name": idx_name,
                            "definition": idx_def,
                        })

        finally:
            engine.dispose()

        return {
            "tables": list(tables_meta.values()),
            "relationships": relationships,
            "total_tables": len(tables_meta),
        }

    @classmethod
    def _introspect_mysql(cls, conn: DatabaseConnection) -> Dict[str, Any]:
        url = ConnectionService.get_connection_url(conn)
        engine = create_engine(url, pool_pre_ping=True)

        tables_meta: Dict[str, Dict[str, Any]] = {}
        relationships: List[Dict[str, Any]] = []

        try:
            with engine.connect() as connection:
                # 1. Fetch tables and views
                tables_query = text("""
                    SELECT 
                        t.TABLE_NAME,
                        t.TABLE_TYPE,
                        COALESCE(t.TABLE_ROWS, 0) as row_count,
                        COALESCE(t.TABLE_COMMENT, '') as table_comment
                    FROM information_schema.TABLES t
                    WHERE t.TABLE_SCHEMA = :db_name
                    ORDER BY t.TABLE_NAME;
                """)
                for row in connection.execute(tables_query, {"db_name": conn.database_name}):
                    tbl_name = row[0]
                    tbl_type = row[1]
                    row_cnt = max(0, int(row[2]))
                    comment = row[3] or ""

                    tables_meta[tbl_name] = {
                        "name": tbl_name,
                        "schema": conn.database_name,
                        "type": "table" if "TABLE" in tbl_type.upper() else "view",
                        "row_count": row_cnt,
                        "description": comment,
                        "columns": [],
                        "primary_key": [],
                        "foreign_keys": [],
                        "indexes": [],
                        "unique_constraints": [],
                    }

                # 2. Fetch columns
                cols_query = text("""
                    SELECT 
                        c.TABLE_NAME,
                        c.COLUMN_NAME,
                        c.DATA_TYPE,
                        c.IS_NULLABLE,
                        c.COLUMN_DEFAULT,
                        COALESCE(c.COLUMN_COMMENT, '') as col_comment
                    FROM information_schema.COLUMNS c
                    WHERE c.TABLE_SCHEMA = :db_name
                    ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
                """)
                for row in connection.execute(cols_query, {"db_name": conn.database_name}):
                    tbl_name = row[0]
                    if tbl_name in tables_meta:
                        col_info = {
                            "name": row[1],
                            "data_type": row[2],
                            "is_nullable": (row[3] == "YES"),
                            "default_value": row[4],
                            "description": row[5] or "",
                        }
                        tables_meta[tbl_name]["columns"].append(col_info)

                # 3. Fetch primary keys
                pk_query = text("""
                    SELECT
                        kcu.TABLE_NAME, 
                        kcu.COLUMN_NAME
                    FROM information_schema.TABLE_CONSTRAINTS tc
                    JOIN information_schema.KEY_COLUMN_USAGE kcu
                        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                        AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                    WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                        AND tc.TABLE_SCHEMA = :db_name
                    ORDER BY kcu.TABLE_NAME, kcu.ORDINAL_POSITION;
                """)
                for row in connection.execute(pk_query, {"db_name": conn.database_name}):
                    tbl_name = row[0]
                    col_name = row[1]
                    if tbl_name in tables_meta:
                        tables_meta[tbl_name]["primary_key"].append(col_name)

                # 4. Fetch foreign keys
                fk_query = text("""
                    SELECT
                        kcu.TABLE_NAME as source_table,
                        kcu.COLUMN_NAME as source_column,
                        kcu.REFERENCED_TABLE_NAME as target_table,
                        kcu.REFERENCED_COLUMN_NAME as target_column,
                        kcu.CONSTRAINT_NAME as constraint_name
                    FROM information_schema.KEY_COLUMN_USAGE kcu
                    WHERE kcu.REFERENCED_TABLE_NAME IS NOT NULL
                        AND kcu.TABLE_SCHEMA = :db_name;
                """)
                for row in connection.execute(fk_query, {"db_name": conn.database_name}):
                    src_tbl = row[0]
                    src_col = row[1]
                    tgt_tbl = row[2]
                    tgt_col = row[3]
                    c_name = row[4]

                    if src_tbl in tables_meta:
                        tables_meta[src_tbl]["foreign_keys"].append({
                            "column": src_col,
                            "target_table": tgt_tbl,
                            "target_column": tgt_col,
                            "constraint_name": c_name,
                        })

                        relationships.append({
                            "id": f"{src_tbl}_{src_col}_to_{tgt_tbl}_{tgt_col}",
                            "source_table": src_tbl,
                            "source_column": src_col,
                            "target_table": tgt_tbl,
                            "target_column": tgt_col,
                            "type": "many_to_one",
                        })

                # 5. Fetch indexes
                idx_query = text("""
                    SELECT 
                        TABLE_NAME,
                        INDEX_NAME,
                        COLUMN_NAME,
                        NON_UNIQUE
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = :db_name
                    ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
                """)
                for row in connection.execute(idx_query, {"db_name": conn.database_name}):
                    tbl_name = row[0]
                    idx_name = row[1]
                    col_name = row[2]
                    is_unique = (row[3] == 0)

                    if tbl_name in tables_meta:
                        existing = next((i for i in tables_meta[tbl_name]["indexes"] if i["name"] == idx_name), None)
                        if existing:
                            existing["columns"].append(col_name)
                        else:
                            tables_meta[tbl_name]["indexes"].append({
                                "name": idx_name,
                                "is_unique": is_unique,
                                "columns": [col_name],
                            })
        finally:
            engine.dispose()

        return {
            "tables": list(tables_meta.values()),
            "relationships": relationships,
            "total_tables": len(tables_meta),
        }

    @classmethod
    def get_table_preview(
        cls, conn: DatabaseConnection, table_name: str, limit: int = 10
    ) -> Dict[str, Any]:
        """Provides a safe, bounded preview of rows from a specific table."""
        # Sanitize table name against alpha-numeric and underscores only
        if not table_name.replace("_", "").isalnum():
            raise ValueError(f"Invalid table identifier: {table_name}")

        safe_limit = min(max(1, limit), 50)
        url = ConnectionService.get_connection_url(conn)
        engine = create_engine(url, pool_pre_ping=True)

        try:
            with engine.connect() as connection:
                if conn.database_type.lower() == "postgresql":
                    query = text(f'SELECT * FROM public."{table_name}" LIMIT :limit;')
                else:
                    query = text(f'SELECT * FROM `{table_name}` LIMIT :limit;')
                result = connection.execute(query, {"limit": safe_limit})
                columns = list(result.keys())
                rows = [list(row) for row in result.fetchall()]
                # Convert non-serializable objects (datetime, Decimal, UUID) to string
                cleaned_rows = []
                for r in rows:
                    cleaned_rows.append([str(val) if val is not None else None for val in r])

                return {
                    "table_name": table_name,
                    "columns": columns,
                    "rows": cleaned_rows,
                    "row_count": len(cleaned_rows),
                }
        finally:
            engine.dispose()

    @classmethod
    def generate_er_diagram_data(cls, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Formats snapshot data into React Flow nodes and edges."""
        tables = snapshot_data.get("tables", [])
        relationships = snapshot_data.get("relationships", [])

        nodes = []
        # Grid layout coordinates
        cols_per_row = 3
        card_width = 320
        card_height = 280
        spacing_x = 80
        spacing_y = 60

        for i, table in enumerate(tables):
            grid_x = (i % cols_per_row) * (card_width + spacing_x) + 50
            grid_y = (i // cols_per_row) * (card_height + spacing_y) + 50

            columns = []
            pks = set(table.get("primary_key", []))
            for col in table.get("columns", []):
                columns.append({
                    "name": col["name"],
                    "data_type": col["data_type"],
                    "is_primary": col["name"] in pks,
                    "is_nullable": col.get("is_nullable", True),
                })

            nodes.append({
                "id": table["name"],
                "type": "tableNode",
                "position": {"x": grid_x, "y": grid_y},
                "data": {
                    "label": table["name"],
                    "row_count": table.get("row_count", 0),
                    "description": table.get("description", ""),
                    "columns": columns,
                    "primary_key": list(pks),
                },
            })

        edges = []
        for i, rel in enumerate(relationships):
            edges.append({
                "id": f"edge-{rel['source_table']}-{rel['source_column']}-{rel['target_table']}",
                "source": rel["source_table"],
                "target": rel["target_table"],
                "label": f"{rel['source_column']} → {rel['target_column']}",
                "animated": True,
                "style": {"stroke": "#8B5CF6", "strokeWidth": 2},
            })

        return {"nodes": nodes, "edges": edges}

    @classmethod
    def sync_and_save_snapshot(
        cls, db: Session, conn: DatabaseConnection
    ) -> Tuple[SchemaSnapshot, Dict[str, Any]]:
        """Introspects external schema and records snapshot with version tracking."""
        snapshot_data = cls.introspect_connection(conn)

        # Get latest version for this connection
        last_snapshot = (
            db.query(SchemaSnapshot)
            .filter(SchemaSnapshot.connection_id == conn.id)
            .order_by(SchemaSnapshot.schema_version.desc())
            .first()
        )
        new_version = (last_snapshot.schema_version + 1) if last_snapshot else 1

        snapshot = SchemaSnapshot(
            connection_id=conn.id,
            schema_version=new_version,
            snapshot_data=snapshot_data,
        )
        db.add(snapshot)
        conn.status = "connected"
        db.commit()
        db.refresh(snapshot)

        return snapshot, snapshot_data

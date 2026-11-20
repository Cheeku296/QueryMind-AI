import logging
import uuid
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.ai.embeddings import EMBEDDING_DIMENSION, embedding_provider
from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    def __init__(self, url: Optional[str] = None, collection_name: Optional[str] = None):
        self.url = url or settings.QDRANT_URL
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.client = QdrantClient(url=self.url, api_key=settings.QDRANT_API_KEY)
        self.ensure_collection()

    def ensure_collection(self):
        """Ensures the Qdrant collection exists with the correct vector configuration."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                # Create payload indexes for fast filtered searches
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="workspace_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="connection_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="doc_type",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Error checking/creating Qdrant collection: {e}")

    def index_database_schema(
        self,
        workspace_id: str,
        connection_id: str,
        snapshot_data: Dict[str, Any],
    ) -> int:
        """Indexes table, column, and relationship metadata into Qdrant."""
        self.ensure_collection()
        points: List[qmodels.PointStruct] = []
        tables = snapshot_data.get("tables", [])
        relationships = snapshot_data.get("relationships", [])

        # 1. Index each table with full column metadata
        for table in tables:
            tbl_name = table["name"]
            desc = table.get("description", "")
            cols = table.get("columns", [])
            col_names = [c["name"] for c in cols]
            pks = table.get("primary_key", [])
            fks = table.get("foreign_keys", [])

            # Rich semantic document text
            col_details = ", ".join([f"{c['name']} ({c['data_type']})" for c in cols])
            fk_details = ", ".join([f"{fk['column']} -> {fk['target_table']}.{fk['target_column']}" for fk in fks])
            content = (
                f"Table: {tbl_name}. Description: {desc}. "
                f"Columns: {col_details}. Primary Keys: {', '.join(pks)}. "
                f"Foreign Keys: {fk_details}."
            )

            vector = embedding_provider.embed_text(content)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{connection_id}:{tbl_name}"))

            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "workspace_id": str(workspace_id),
                        "connection_id": str(connection_id),
                        "doc_type": "table",
                        "table_name": tbl_name,
                        "description": desc,
                        "columns": cols,
                        "primary_key": pks,
                        "foreign_keys": fks,
                        "content": content,
                    },
                )
            )

            # 2. Index key columns individually for granular keyword/semantic search
            for col in cols:
                col_content = (
                    f"Column {col['name']} in table {tbl_name}. Data type: {col['data_type']}. "
                    f"Description: {col.get('description', '')}. Is primary key: {col['name'] in pks}."
                )
                col_vector = embedding_provider.embed_text(col_content)
                col_point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{connection_id}:{tbl_name}:{col['name']}"))
                points.append(
                    qmodels.PointStruct(
                        id=col_point_id,
                        vector=col_vector,
                        payload={
                            "workspace_id": str(workspace_id),
                            "connection_id": str(connection_id),
                            "doc_type": "column",
                            "table_name": tbl_name,
                            "column_name": col["name"],
                            "data_type": col["data_type"],
                            "content": col_content,
                        },
                    )
                )

        # 3. Index relationships
        for rel in relationships:
            rel_content = (
                f"Relationship: Table {rel['source_table']} joins with table {rel['target_table']} "
                f"on {rel['source_table']}.{rel['source_column']} = {rel['target_table']}.{rel['target_column']}."
            )
            rel_vector = embedding_provider.embed_text(rel_content)
            rel_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{connection_id}:rel:{rel['source_table']}:{rel['target_table']}"))
            points.append(
                qmodels.PointStruct(
                    id=rel_id,
                    vector=rel_vector,
                    payload={
                        "workspace_id": str(workspace_id),
                        "connection_id": str(connection_id),
                        "doc_type": "relationship",
                        "source_table": rel["source_table"],
                        "target_table": rel["target_table"],
                        "source_column": rel["source_column"],
                        "target_column": rel["target_column"],
                        "content": rel_content,
                    },
                )
            )

        # Upsert in batches of 50
        batch_size = 50
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=self.collection_name, points=batch)

        logger.info(f"Indexed {len(points)} schema documents for connection {connection_id} in Qdrant.")
        return len(points)

    def index_glossary_term(
        self,
        workspace_id: str,
        connection_id: Optional[str],
        term_id: str,
        term: str,
        definition: str,
        associated_tables: List[str],
        associated_columns: List[str],
        example_sql: Optional[str] = None,
    ) -> str:
        """Indexes a business glossary term into Qdrant."""
        self.ensure_collection()
        content = (
            f"Business Glossary Term: {term}. Definition: {definition}. "
            f"Associated Tables: {', '.join(associated_tables)}. "
            f"Associated Columns: {', '.join(associated_columns)}. "
            f"Example SQL: {example_sql or 'None'}."
        )
        vector = embedding_provider.embed_text(content)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"glossary:{term_id}"))

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "workspace_id": str(workspace_id),
                        "connection_id": str(connection_id) if connection_id else "all",
                        "doc_type": "glossary",
                        "term_id": str(term_id),
                        "term": term,
                        "definition": definition,
                        "associated_tables": associated_tables,
                        "associated_columns": associated_columns,
                        "example_sql": example_sql,
                        "content": content,
                    },
                )
            ],
        )
        return point_id

    def delete_glossary_term(self, term_id: str):
        """Removes a glossary term from vector storage."""
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"glossary:{term_id}"))
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.PointIdsList(points=[point_id]),
            )
        except Exception as e:
            logger.warning(f"Failed to delete glossary term point {point_id}: {e}")

    def delete_connection_index(self, workspace_id: str, connection_id: str):
        """Deletes all indexed vectors for a database connection."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="workspace_id",
                                match=qmodels.MatchValue(value=str(workspace_id)),
                            ),
                            qmodels.FieldCondition(
                                key="connection_id",
                                match=qmodels.MatchValue(value=str(connection_id)),
                            ),
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to delete connection index: {e}")

    def retrieve_relevant_schema(
        self,
        workspace_id: str,
        connection_id: str,
        query: str,
        limit: int = 6,
    ) -> Dict[str, Any]:
        """Performs vector search in Qdrant and constructs compact schema context for generation."""
        query_vector = embedding_provider.embed_text(query)

        filter_condition = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="workspace_id",
                    match=qmodels.MatchValue(value=str(workspace_id)),
                ),
                qmodels.FieldCondition(
                    key="connection_id",
                    match=qmodels.MatchAny(any=[str(connection_id), "all"]),
                ),
            ]
        )

        try:
            # Qdrant client search (using query_points in newer qdrant-client)
            if hasattr(self.client, "query_points"):
                search_res = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=filter_condition,
                    limit=limit * 2,
                ).points
            else:
                search_res = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=filter_condition,
                    limit=limit * 2,
                )
        except Exception as e:
            logger.warning(f"Vector search failed: {e}. Falling back to empty results.")
            search_res = []

        tables_matched = {}
        relationships_matched = []
        glossary_matched = []

        for hit in search_res:
            payload = hit.payload or {}
            doc_type = payload.get("doc_type")
            score = getattr(hit, "score", 0.0)

            if doc_type == "table":
                tbl = payload.get("table_name")
                if tbl and tbl not in tables_matched:
                    tables_matched[tbl] = {
                        "table_name": tbl,
                        "description": payload.get("description", ""),
                        "columns": payload.get("columns", []),
                        "primary_key": payload.get("primary_key", []),
                        "foreign_keys": payload.get("foreign_keys", []),
                        "score": score,
                    }
            elif doc_type == "column":
                tbl = payload.get("table_name")
                if tbl and tbl not in tables_matched:
                    tables_matched[tbl] = {
                        "table_name": tbl,
                        "description": "",
                        "columns": [{"name": payload.get("column_name"), "data_type": payload.get("data_type")}],
                        "primary_key": [],
                        "foreign_keys": [],
                        "score": score,
                    }
            elif doc_type == "relationship":
                relationships_matched.append({
                    "source_table": payload.get("source_table"),
                    "source_column": payload.get("source_column"),
                    "target_table": payload.get("target_table"),
                    "target_column": payload.get("target_column"),
                    "score": score,
                })
            elif doc_type == "glossary":
                glossary_matched.append({
                    "term": payload.get("term"),
                    "definition": payload.get("definition"),
                    "associated_tables": payload.get("associated_tables", []),
                    "associated_columns": payload.get("associated_columns", []),
                    "example_sql": payload.get("example_sql"),
                    "score": score,
                })

        # Format compact prompt context
        context_parts = []
        if tables_matched:
            context_parts.append("RELEVANT TABLES & SCHEMAS:")
            for t_name, t_info in tables_matched.items():
                col_defs = ", ".join([f"{c['name']} ({c.get('data_type', 'text')})" for c in t_info.get("columns", [])])
                pk_str = f" [PK: {', '.join(t_info.get('primary_key', []))}]" if t_info.get("primary_key") else ""
                fk_strs = [f"{fk['column']} -> {fk['target_table']}.{fk['target_column']}" for fk in t_info.get("foreign_keys", [])]
                fk_str = f" [FKs: {', '.join(fk_strs)}]" if fk_strs else ""
                desc_str = f" - Description: {t_info['description']}" if t_info.get("description") else ""
                context_parts.append(f"- {t_name}{desc_str}: {col_defs}{pk_str}{fk_str}")

        if relationships_matched:
            context_parts.append("\nTABLE RELATIONSHIPS / JOINS:")
            for r in relationships_matched:
                context_parts.append(f"- {r['source_table']}.{r['source_column']} = {r['target_table']}.{r['target_column']}")

        if glossary_matched:
            context_parts.append("\nBUSINESS GLOSSARY & DEFINITIONS:")
            for g in glossary_matched:
                context_parts.append(f"- {g['term']}: {g['definition']} (Relevant Tables: {', '.join(g['associated_tables'])})")
                if g.get("example_sql"):
                    context_parts.append(f"  Example SQL Pattern: {g['example_sql']}")

        return {
            "tables": list(tables_matched.values()),
            "relationships": relationships_matched,
            "glossary": glossary_matched,
            "compact_context": "\n".join(context_parts),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns collection stats."""
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return {
                "collection_name": self.collection_name,
                "status": str(info.status),
                "vectors_count": getattr(info, "vectors_count", getattr(info, "points_count", 0)),
                "points_count": getattr(info, "points_count", 0),
            }
        except Exception as e:
            return {"error": str(e), "collection_name": self.collection_name}


qdrant_manager = QdrantManager()


import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.ai.rag.qdrant_manager import qdrant_manager
from app.models.glossary import BusinessGlossary

logger = logging.getLogger(__name__)


class GlossaryService:
    @staticmethod
    def get_terms(
        db: Session,
        workspace_id: Any,
        connection_id: Optional[Any] = None,
        search: Optional[str] = None,
    ) -> List[BusinessGlossary]:
        query = db.query(BusinessGlossary).filter(BusinessGlossary.workspace_id == workspace_id)
        if connection_id:
            query = query.filter(
                (BusinessGlossary.connection_id == connection_id) | (BusinessGlossary.connection_id.is_(None))
            )
        if search:
            query = query.filter(
                BusinessGlossary.term.ilike(f"%{search}%") | BusinessGlossary.definition.ilike(f"%{search}%")
            )
        return query.order_by(BusinessGlossary.term.asc()).all()

    @staticmethod
    def create_term(
        db: Session,
        workspace_id: Any,
        term: str,
        definition: str,
        associated_tables: List[str],
        associated_columns: List[str],
        connection_id: Optional[Any] = None,
        example_sql: Optional[str] = None,
    ) -> BusinessGlossary:
        entry = BusinessGlossary(
            workspace_id=workspace_id,
            connection_id=connection_id,
            term=term.strip(),
            definition=definition.strip(),
            associated_tables=associated_tables or [],
            associated_columns=associated_columns or [],
            example_sql=example_sql.strip() if example_sql else None,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        # Index in Qdrant
        try:
            qdrant_manager.index_glossary_term(
                workspace_id=str(workspace_id),
                connection_id=str(connection_id) if connection_id else None,
                term_id=str(entry.id),
                term=entry.term,
                definition=entry.definition,
                associated_tables=entry.associated_tables,
                associated_columns=entry.associated_columns,
                example_sql=entry.example_sql,
            )
        except Exception as e:
            logger.warning(f"Failed to vector index glossary term '{term}': {e}")

        return entry

    @staticmethod
    def update_term(
        db: Session,
        term_id: Any,
        term: Optional[str] = None,
        definition: Optional[str] = None,
        associated_tables: Optional[List[str]] = None,
        associated_columns: Optional[List[str]] = None,
        example_sql: Optional[str] = None,
    ) -> Optional[BusinessGlossary]:
        entry = db.query(BusinessGlossary).filter(BusinessGlossary.id == term_id).first()
        if not entry:
            return None

        if term is not None:
            entry.term = term.strip()
        if definition is not None:
            entry.definition = definition.strip()
        if associated_tables is not None:
            entry.associated_tables = associated_tables
        if associated_columns is not None:
            entry.associated_columns = associated_columns
        if example_sql is not None:
            entry.example_sql = example_sql.strip() if example_sql else None

        db.commit()
        db.refresh(entry)

        # Re-index in Qdrant
        try:
            qdrant_manager.index_glossary_term(
                workspace_id=str(entry.workspace_id),
                connection_id=str(entry.connection_id) if entry.connection_id else None,
                term_id=str(entry.id),
                term=entry.term,
                definition=entry.definition,
                associated_tables=entry.associated_tables,
                associated_columns=entry.associated_columns,
                example_sql=entry.example_sql,
            )
        except Exception as e:
            logger.warning(f"Failed to re-index glossary term '{entry.term}': {e}")

        return entry

    @staticmethod
    def delete_term(db: Session, term_id: Any) -> bool:
        entry = db.query(BusinessGlossary).filter(BusinessGlossary.id == term_id).first()
        if not entry:
            return False

        qdrant_manager.delete_glossary_term(str(term_id))
        db.delete(entry)
        db.commit()
        return True


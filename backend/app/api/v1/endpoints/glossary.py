import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace_member, require_role
from app.core.database import get_sync_db
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.glossary import GlossaryCreate, GlossaryResponse, GlossaryUpdate
from app.services.glossary_service import GlossaryService

router = APIRouter()


@router.get("", response_model=List[GlossaryResponse])
def list_glossary_terms(
    connection_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Retrieves business glossary terms for the workspace."""
    return GlossaryService.get_terms(
        db=db,
        workspace_id=member.workspace_id,
        connection_id=connection_id,
        search=search,
    )


@router.post("", response_model=GlossaryResponse)
def create_glossary_term(
    req: GlossaryCreate,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Creates a business glossary term and indexes it into Qdrant."""
    entry = GlossaryService.create_term(
        db=db,
        workspace_id=member.workspace_id,
        connection_id=req.connection_id,
        term=req.term,
        definition=req.definition,
        associated_tables=req.associated_tables,
        associated_columns=req.associated_columns,
        example_sql=req.example_sql,
    )
    return entry


@router.patch("/{term_id}", response_model=GlossaryResponse)
def update_glossary_term(
    term_id: uuid.UUID,
    req: GlossaryUpdate,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Updates a business glossary term and re-indexes into Qdrant."""
    updated = GlossaryService.update_term(
        db=db,
        term_id=term_id,
        term=req.term,
        definition=req.definition,
        associated_tables=req.associated_tables,
        associated_columns=req.associated_columns,
        example_sql=req.example_sql,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Glossary term not found.")
    return updated


@router.delete("/{term_id}")
def delete_glossary_term(
    term_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Deletes a business glossary term and removes it from Qdrant."""
    success = GlossaryService.delete_term(db=db, term_id=term_id)
    if not success:
        raise HTTPException(status_code=404, detail="Glossary term not found.")
    return {"message": "Glossary term deleted."}

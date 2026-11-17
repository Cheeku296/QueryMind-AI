import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ReportGenerateRequest(BaseModel):
    connection_id: uuid.UUID
    title: str
    report_type: str = "analytical"  # summary, analytical, trend, comparative
    sql_query: Optional[str] = None
    question: Optional[str] = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    report_type: str
    report_content: Dict[str, Any]
    file_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

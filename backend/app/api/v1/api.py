from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    analytics,
    auth,
    chat,
    connections,
    glossary,
    queries,
    reports,
    saved_queries,
    schema,
    settings,
    sql,
    workspaces,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(connections.router, prefix="/connections", tags=["Database Connections"])
api_router.include_router(schema.router, prefix="", tags=["Schema Intelligence"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI SQL Assistant"])
api_router.include_router(sql.router, prefix="/sql", tags=["SQL Engine"])
api_router.include_router(queries.router, prefix="/queries", tags=["Query History"])
api_router.include_router(saved_queries.router, prefix="/saved-queries", tags=["Saved Queries"])
api_router.include_router(glossary.router, prefix="/glossary", tags=["Business Glossary"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agent Execution Monitor"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(settings.router, prefix="", tags=["Settings & Health"])

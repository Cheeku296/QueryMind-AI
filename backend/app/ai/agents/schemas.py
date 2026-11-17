from typing import List, Optional
from pydantic import BaseModel, Field


class SQLGenerationOutput(BaseModel):
    """Structured response from Gemini SQL Generation Agent."""
    sql: str = Field(description="The executable SQL query in the target dialect (PostgreSQL).")
    dialect: str = Field(default="postgresql", description="SQL dialect identifier.")
    explanation: str = Field(description="Clear explanation of how the query computes the user question.")
    tables_used: List[str] = Field(default_factory=list, description="Names of all tables accessed in the query.")
    columns_used: List[str] = Field(default_factory=list, description="Names of all columns accessed in the query.")
    assumptions: List[str] = Field(default_factory=list, description="Any assumptions made regarding business rules or defaults.")
    requires_clarification: bool = Field(default=False, description="True if the request is ambiguous and needs user input.")
    clarification_question: Optional[str] = Field(default=None, description="Question to ask user if clarification is required.")


class SupervisorOutput(BaseModel):
    """Structured response from Supervisor Agent."""
    intent: str = Field(
        description="Category of the user request: sql_generation, sql_explanation, query_optimization, data_analysis, schema_question, general_assistance"
    )
    confidence: float = Field(default=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Brief explanation of the routing decision.")
    extracted_entities: List[str] = Field(default_factory=list, description="Key tables, metrics, or entities identified in the prompt.")


class ResultAnalysisOutput(BaseModel):
    """Structured response from Result Analysis Agent."""
    summary: str = Field(description="Concise executive summary of the query results.")
    key_findings: List[str] = Field(default_factory=list, description="Specific factual takeaways derived directly from the data rows.")
    trends: List[str] = Field(default_factory=list, description="Noteworthy directional patterns or distributions.")
    anomalies: List[str] = Field(default_factory=list, description="Outliers or surprising values supported strictly by the data.")
    limitations: List[str] = Field(default_factory=list, description="Caveats, sample limitations, or data scope considerations.")


class VisualizationOutput(BaseModel):
    """Structured response from Visualization Agent."""
    chart_type: str = Field(
        description="Recommended chart type: bar, horizontal_bar, line, area, pie, donut, scatter, kpi"
    )
    title: str = Field(description="Descriptive chart title.")
    x_axis: str = Field(description="Column name to use for the X-axis or categorical dimension.")
    y_axis: str = Field(description="Column name to use for the Y-axis or quantitative metric.")
    secondary_y_axis: Optional[str] = Field(default=None, description="Optional secondary metric column.")
    reason: str = Field(description="Rationale for choosing this visualization format.")


class SQLCorrectionOutput(BaseModel):
    """Structured response from SQL Correction Agent."""
    corrected_sql: str = Field(description="The revised SQL statement resolving the previous error.")
    explanation_of_fix: str = Field(description="Explanation of the fix made.")
    tables_used: List[str] = Field(default_factory=list, description="Tables used in the corrected query.")

export interface User {
  id: string;
  name: string;
  email: string;
  status: string;
  created_at: string;
  workspace_id?: string;
  workspace_name?: string;
  role?: string;
}

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  role: 'ADMIN' | 'EDITOR' | 'VIEWER';
  created_at: string;
}

export interface DatabaseConnection {
  id: string;
  workspace_id: string;
  name: string;
  database_type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  status: 'connected' | 'disconnected' | 'testing' | 'failed' | 'sync_required';
  created_at: string;
  updated_at: string;
}

export interface TableColumn {
  name: string;
  data_type: string;
  is_nullable: boolean;
  default_value?: string;
  description?: string;
  is_primary?: boolean;
}

export interface TableMetadata {
  name: string;
  description?: string;
  row_count: number;
  columns_count?: number;
  columns?: TableColumn[];
  primary_key?: string[];
  foreign_keys?: Array<{
    column: string;
    target_table: string;
    target_column: string;
  }>;
}

export interface TableRelationship {
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  relationship_type?: string;
}

export interface MessageMetadata {
  analysis?: {
    summary?: string;
    key_findings?: string[];
    trends?: string[];
    anomalies?: string[];
    limitations?: string[];
  };
  chart?: {
    chart_type: string;
    title: string;
    x_axis: string;
    y_axis: string;
    data: any[];
  };
  execution_result?: {
    success: boolean;
    columns: string[];
    rows: any[][];
    row_count: number;
    execution_time_ms: number;
    error?: string;
  };
  validation_result?: {
    is_valid: boolean;
    errors?: string[];
    warnings?: string[];
    tables_used?: string[];
  };
  node_events?: Array<{
    node: string;
    status: string;
    duration_ms?: number;
    output?: string;
    message?: string;
  }>;
  run_id?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  generated_sql?: string;
  execution_status?: string;
  created_at: string;
  analysis?: any;
  chart?: any;
  execution_result?: any;
  validation_result?: any;
  node_events?: any[];
}

export interface Conversation {
  id: string;
  title: string;
  connection_id?: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface QueryRecord {
  id: string;
  connection_id: string;
  connection_name?: string;
  user_name?: string;
  original_question?: string;
  generated_sql?: string;
  executed_sql: string;
  status: 'success' | 'failed' | 'rejected';
  execution_time_ms: number;
  row_count: number;
  error_message?: string;
  created_at: string;
}

export interface SavedQuery {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string;
  description?: string;
  sql: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface GlossaryTerm {
  id: string;
  workspace_id: string;
  connection_id?: string;
  term: string;
  definition: string;
  associated_tables: string[];
  associated_columns: string[];
  example_sql?: string;
  created_at: string;
  updated_at: string;
}

export interface ReportItem {
  id: string;
  workspace_id: string;
  title: string;
  report_type: string;
  report_content: {
    title: string;
    executive_summary: string;
    objective?: string;
    database_source?: string;
    sql_query?: string;
    key_metrics?: Record<string, any>;
    findings?: string[];
    columns?: string[];
    sample_rows?: any[][];
    limitations?: string[];
  };
  created_at: string;
}

export interface AgentRunItem {
  id: string;
  run_id: string;
  conversation_id?: string;
  status: string;
  current_node: string;
  started_at: string;
  completed_at?: string;
  metadata?: any;
}

export interface CitationItem {
  doc_id: string;
  filename: string;
  page_number?: number | null;
  snippet: string;
}

export interface WebCitation {
  title: string;
  url: string;
  snippet: string;
}

export interface AgentTrace {
  local_agent_used?: boolean;
  web_agent_used?: boolean;
  privacy_verified?: boolean;
  sanitized_query?: string | null;
  redacted_count?: number;
  latency_ms?: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  citations: CitationItem[];
  web_citations?: WebCitation[];
  agent_trace?: AgentTrace | null;
  created_at: string;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  doc_ids: string[];
  message_count: number;
  updated_at: string;
  created_at: string;
}

export interface ChatSessionDetail {
  id: string;
  title: string;
  doc_ids: string[];
  messages: ChatMessage[];
  updated_at: string;
  created_at: string;
}

export interface SendMessageResponse {
  session: ChatSessionSummary;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export interface DocumentItem {
  doc_id: string;
  filename: string;
  file_size: number;
  page_count: number;
  extraction_status:
    | "uploaded"
    | "queued"
    | "parsing"
    | "extracting"
    | "completed"
    | "failed";
  entity_count: number;
  relationship_count: number;
  summary: string;
  created_at: string;
  synced_to_neo4j?: boolean;
}

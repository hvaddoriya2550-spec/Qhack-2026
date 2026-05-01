export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  agentName?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface AgentAction {
  agentName: string;
  action: string;
  input?: Record<string, unknown>;
  output?: string;
  timestamp: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
}

export interface ChatRequest {
  conversation_id?: string;
  project_id?: string;
  message: string;
  agent_id?: string;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  agent_actions: AgentAction[];
  metadata: Record<string, unknown>;
}

export interface StreamEvent {
  type:
    | "agent_selected"
    | "message"
    | "tool_call"
    | "thinking"
    | "done"
    | "error"
    | "phase_changed"
    | "data_extracted"
    | "search_result"
    | "deliverable_ready"
    | "project_created";
  content?: string;
  agent?: string;
  phase?: string;
  project_id?: string;
  deliverable_id?: string;
  metadata?: Record<string, unknown>;
}

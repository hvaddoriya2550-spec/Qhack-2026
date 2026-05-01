import type { ChatRequest, ChatResponse, Conversation } from "../types/chat";
import type { AgentInfo } from "../types/agent";
import type { Project, ProjectCreate, Deliverable } from "../types/project";

const BASE_URL = (import.meta.env.VITE_API_URL || "") + "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export const api = {
  chat: {
    send: (data: ChatRequest) =>
      request<ChatResponse>("/chat/", { method: "POST", body: JSON.stringify(data) }),
  },

  conversations: {
    list: () => request<Conversation[]>("/conversations/"),
    get: (id: string) => request<Conversation>(`/conversations/${id}`),
    delete: (id: string) =>
      request<{ deleted: boolean }>(`/conversations/${id}`, { method: "DELETE" }),
  },

  agents: {
    list: () => request<AgentInfo[]>("/agents/"),
    get: (id: string) => request<AgentInfo>(`/agents/${id}`),
  },

  projects: {
    list: () => request<Project[]>("/projects/"),
    get: (id: string) => request<Project>(`/projects/${id}`),
    create: (data: ProjectCreate) =>
      request<Project>("/projects/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<ProjectCreate>) =>
      request<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    getConversation: async (projectId: string): Promise<string | null> => {
      try {
        const data = await request<{ conversation_id: string }>(
          `/projects/${projectId}/conversation`,
        );
        return data.conversation_id;
      } catch {
        return null; // No existing conversation
      }
    },
  },

  deliverables: {
    get: (id: string) => request<Deliverable>(`/deliverables/${id}`),
    listByProject: (projectId: string) =>
      request<Deliverable[]>(`/deliverables/project/${projectId}`),
    downloadUrl: (id: string) => `${BASE_URL}/deliverables/${id}/download`,
  },

  report: {
    generate: (projectId: string) =>
      request<Record<string, unknown>>(`/report/generate/${projectId}`, { method: "POST" }),
  },

  voice: {
    transcribe: async (blob: Blob): Promise<string> => {
      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");
      const response = await fetch(`${BASE_URL}/voice/transcribe`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Transcription failed");
      const data = await response.json();
      return data.text;
    },
  },
};

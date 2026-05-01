import { create } from "zustand";
import type { Message, Conversation } from "../types/chat";

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  activeAgent: string | null;
  currentPhase: string | null;

  setConversations: (conversations: Conversation[]) => void;
  setActiveConversation: (id: string | null) => void;
  addMessage: (message: Message) => void;
  setIsStreaming: (streaming: boolean) => void;
  setActiveAgent: (agent: string | null) => void;
  setCurrentPhase: (phase: string | null) => void;
  appendToLastMessage: (content: string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  activeAgent: null,
  currentPhase: null,

  setConversations: (conversations) => set({ conversations }),
  setActiveConversation: (id) => set({ activeConversationId: id }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setActiveAgent: (activeAgent) => set({ activeAgent }),
  setCurrentPhase: (currentPhase) => set({ currentPhase }),
  appendToLastMessage: (content) =>
    set((state) => {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last) {
        messages[messages.length - 1] = { ...last, content: last.content + content };
      }
      return { messages };
    }),
  clearMessages: () => set({ messages: [], activeAgent: null }),
}));

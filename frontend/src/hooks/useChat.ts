import { useCallback, useEffect, useRef } from "react";
import { useChatStore } from "../store/chatStore";
import { api } from "../services/api";
import { createChatSocket } from "../services/websocket";
import type { Message, StreamEvent } from "../types/chat";

export function useChat(projectId?: string) {
  const store = useChatStore();
  const wsRef = useRef<WebSocket | null>(null);
  const initializedRef = useRef(false);

  // Welcome message for no-project chat
  useEffect(() => {
    if (projectId || initializedRef.current) return;
    if (store.messages.length > 0) return;
    initializedRef.current = true;
    store.addMessage({
      id: crypto.randomUUID(),
      role: "assistant",
      content: "Hey there! I'm Cleo, your AI sales coach. Tell me about the customer you're preparing for — name, location, what product they're interested in — and I'll help you build a winning pitch.",
      agentName: "data_gathering",
      timestamp: new Date().toISOString(),
    });
  }, [projectId, store]);

  // On mount: if we have a projectId, load project phase + existing conversation
  useEffect(() => {
    if (!projectId || initializedRef.current) return;
    initializedRef.current = true;

    // Clear previous chat state but keep phase until loaded
    store.clearMessages();
    store.setActiveConversation(null);

    // Load project phase immediately
    api.projects.get(projectId).then((project) => {
      store.setCurrentPhase(project.status ?? "data_gathering");
    }).catch(() => {
      store.setCurrentPhase("data_gathering");
    });

    // Resume existing conversation and load messages
    api.projects.getConversation(projectId).then(async (convId) => {
      if (convId) {
        store.setActiveConversation(convId);
        // Load existing messages from DB
        try {
          const conv = await api.conversations.get(convId);
          const messages: Message[] = (conv as any).messages?.map((m: any) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            agentName: m.agent_name,
            timestamp: m.created_at || new Date().toISOString(),
          })) || [];
          if (messages.length > 0) {
            for (const msg of messages) {
              store.addMessage(msg);
            }
          } else {
            // Existing conversation but no messages — add welcome
            addWelcome();
          }
        } catch {
          addWelcome();
        }
      } else {
        // No conversation yet — add welcome message
        addWelcome();
      }
    });

    function addWelcome() {
      api.projects.get(projectId!).then((project) => {
        const hasData = (project.status as string) !== "data_gathering" && project.status !== "gathering";
        const name = (project as any).customer_name;
        const msg = hasData
          ? `Hey there! I'm Cleo, your AI sales coach. I've already got the details on ${name || "this lead"} — just say the word and I'll research the market, build your strategy, and prep your pitch. What would you like to start with?`
          : "Hey there! I'm Cleo, your AI sales coach. Let's get started — tell me about the customer you're visiting. What's their name and where are they located?";
        store.addMessage({
          id: crypto.randomUUID(),
          role: "assistant",
          content: msg,
          agentName: hasData ? "research" : "data_gathering",
          timestamp: new Date().toISOString(),
        });
      }).catch(() => {
        store.addMessage({
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Hey there! I'm Cleo, your AI sales coach. Tell me about the customer you're preparing for — name, location, what product they're interested in.",
          agentName: "data_gathering",
          timestamp: new Date().toISOString(),
        });
      });
    }
  }, [projectId, store]);

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      store.addMessage(userMessage);
      store.setIsStreaming(true);

      try {
      const response = await api.chat.send({
        conversation_id: store.activeConversationId ?? undefined,
        project_id: projectId ?? undefined,
        message: content,
      });

      // Store the conversation ID for subsequent messages
      if (!store.activeConversationId) {
        store.setActiveConversation(response.conversation_id);
      }

      // Track phase changes
      const phase = response.metadata?.phase as string | undefined;
      if (phase) {
        store.setCurrentPhase(phase);
      }

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.message,
        agentName: response.metadata?.agent_name as string | undefined,
        timestamp: new Date().toISOString(),
        metadata: response.metadata,
      };
      store.addMessage(assistantMessage);
      } finally {
        store.setIsStreaming(false);
      }
    },
    [store, projectId],
  );

  const startStreaming = useCallback(
    (conversationId: string) => {
      store.setIsStreaming(true);

      const ws = createChatSocket(
        conversationId,
        (event: StreamEvent) => {
          switch (event.type) {
            case "agent_selected":
              store.setActiveAgent(event.agent ?? null);
              break;
            case "phase_changed":
              store.setCurrentPhase(event.phase ?? null);
              break;
            case "message":
              store.appendToLastMessage(event.content ?? "");
              break;
            case "done":
              store.setIsStreaming(false);
              store.setActiveAgent(null);
              break;
            case "error":
              store.setIsStreaming(false);
              break;
          }
        },
        () => store.setIsStreaming(false),
      );

      wsRef.current = ws;
    },
    [store],
  );

  const stopStreaming = useCallback(() => {
    wsRef.current?.close();
    store.setIsStreaming(false);
  }, [store]);

  return {
    messages: store.messages,
    isStreaming: store.isStreaming,
    activeAgent: store.activeAgent,
    currentPhase: store.currentPhase,
    sendMessage,
    startStreaming,
    stopStreaming,
  };
}

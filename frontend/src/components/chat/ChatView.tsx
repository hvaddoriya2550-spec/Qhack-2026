import { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MessageSquare, Mic, FileText, Loader2, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { useChat } from "../../hooks/useChat";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import VoiceMode from "./VoiceMode";
import AgentBadge from "../agents/AgentBadge";
import PhaseIndicator from "../agents/PhaseIndicator";

export default function ChatView() {
  const { projectId: urlProjectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [dynamicProjectId, setDynamicProjectId] = useState<string | null>(null);
  const effectiveProjectId = urlProjectId || dynamicProjectId;
  const { messages, isStreaming, activeAgent, currentPhase, sendMessage } = useChat(urlProjectId);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [phaseFlash, setPhaseFlash] = useState(false);
  const [phaseToast, setPhaseToast] = useState<string | null>(null);
  const prevPhaseRef = useRef(currentPhase);

  const phaseLabels: Record<string, string> = {
    data_gathering: "Data Gathering",
    research: "Research",
    analysis: "Analysis",
    financial: "Financing",
    strategy: "Strategy",
    deliverable: "Report",
    complete: "Complete",
  };

  // Flash + toast animation when phase changes
  // Auto-generate report when pipeline completes
  useEffect(() => {
    if (currentPhase && currentPhase !== prevPhaseRef.current) {
      const prev = prevPhaseRef.current;
      prevPhaseRef.current = currentPhase;
      setPhaseFlash(true);
      const t1 = setTimeout(() => setPhaseFlash(false), 1200);

      if (prev) {
        setPhaseToast(`${phaseLabels[prev] || prev} complete — moving to ${phaseLabels[currentPhase] || currentPhase}`);
        const t2 = setTimeout(() => setPhaseToast(null), 3000);
      }


      return () => clearTimeout(t1);
    }
  }, [currentPhase]);

  // Track project_id from auto-created projects (general chat)
  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (lastMsg?.metadata?.project_id && !effectiveProjectId) {
      setDynamicProjectId(lastMsg.metadata.project_id as string);
    }
    if (lastMsg?.metadata?.project_created && lastMsg?.metadata?.project_id) {
      setDynamicProjectId(lastMsg.metadata.project_id as string);
    }
  }, [messages, effectiveProjectId]);

  const canGenerateReport = effectiveProjectId && (
    currentPhase === "strategy" ||
    currentPhase === "deliverable" ||
    currentPhase === "complete"
  );

  const phaseStatusMap: Record<string, string> = {
    data_gathering: "gathering",
    research: "researching",
    analysis: "analyzing",
    financial: "financing",
    strategy: "strategizing",
    deliverable: "complete",
    complete: "complete",
  };
  const displayPhase = currentPhase ? (phaseStatusMap[currentPhase] ?? "gathering") : "gathering";

  const handleGenerateReport = useCallback(async () => {
    if (!effectiveProjectId) return;
    setIsGeneratingReport(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/v1/report/generate/${effectiveProjectId}`, { method: "POST" });
      const data = await res.json();
      localStorage.setItem("reportData", JSON.stringify(data));
      navigate("/report");
    } catch {
      alert("Failed to generate report.");
    } finally {
      setIsGeneratingReport(false);
    }
  }, [effectiveProjectId, navigate]);

  return (
    <div className="flex flex-col flex-1 min-h-0 relative" style={{ background: "#f9fafb" }}>
      {/* Grid overlay like other pages */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        backgroundImage: "linear-gradient(rgba(15,23,42,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(15,23,42,0.03) 1px, transparent 1px)",
        backgroundSize: "40px 40px",
        maskImage: "linear-gradient(to bottom, rgba(0,0,0,0.75), transparent 95%)",
      }} />

      {/* Header — fixed at top */}
      <header className="sticky top-0 z-10 shrink-0 px-6 py-3" style={{ background: "rgba(255,255,255,0.95)", backdropFilter: "blur(12px)", borderBottom: "1px solid #e5e7eb" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Sparkles className="w-4 h-4 text-[#3535F3]" />
            <span className="text-sm font-bold text-gray-800">Cleo</span>
            {activeAgent && <AgentBadge agentName={activeAgent} />}
          </div>

          <div className="flex items-center gap-2">
            {canGenerateReport && (
              <button
                onClick={handleGenerateReport}
                disabled={isGeneratingReport}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-[#3535F3] to-[#4747F5] hover:from-[#4747F5] hover:to-[#5555F7] text-white transition-all shadow-lg shadow-[#3535F3]/20 disabled:opacity-50"
              >
                {isGeneratingReport ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <FileText className="w-3.5 h-3.5" />
                )}
                {isGeneratingReport ? "Generating..." : "Generate Report"}
              </button>
            )}

            {/* Voice / Text mode toggle */}
            <div className="flex items-center bg-gray-100 rounded-xl p-0.5 border border-gray-200">
              <button
                onClick={() => setIsVoiceMode(false)}
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                  !isVoiceMode
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700",
                )}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Text
              </button>
              <button
                onClick={() => setIsVoiceMode(true)}
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                  isVoiceMode
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700",
                )}
              >
                <Mic className="w-3.5 h-3.5" />
                Voice
              </button>
            </div>
          </div>
        </div>

        {/* Phase indicator with flash animation */}
        <div
          className={clsx(
            "mt-4 mb-1 transition-all duration-500 max-w-3xl mx-auto px-6 w-full",
            phaseFlash && "scale-[1.02] brightness-125",
          )}
        >
          <PhaseIndicator status={displayPhase} />
        </div>
      </header>

      {/* Phase transition toast */}
      <AnimatePresence>
        {phaseToast && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="mx-6 mt-2 px-4 py-2.5 rounded-xl bg-[#3535F3]/8 border border-[#3535F3]/15 text-[#3535F3] text-xs font-medium text-center"
          >
            <Sparkles className="w-3 h-3 inline mr-1.5" />
            {phaseToast}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content */}
      {isVoiceMode ? (
        <VoiceMode projectId={effectiveProjectId} />
      ) : (
        <>
          <MessageList messages={messages} isStreaming={isStreaming} />
          <ChatInput onSend={sendMessage} disabled={isStreaming} projectId={effectiveProjectId} />
        </>
      )}
    </div>
  );
}

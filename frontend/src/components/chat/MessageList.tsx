import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Message } from "../../types/chat";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: Message[];
  isStreaming: boolean;
}

function TypingDots() {
  return (
    <motion.div
      className="flex items-center gap-2 px-4 py-3"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center gap-1.5 px-4 py-3 rounded-2xl bg-white border border-gray-200 shadow-sm">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-[#6565FF]"
              animate={{ y: [0, -6, 0] }}
              transition={{
                duration: 0.6,
                repeat: Infinity,
                delay: i * 0.15,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
        <span className="text-gray-500 text-sm ml-2">Cleo is thinking</span>
      </div>
    </motion.div>
  );
}

export default function MessageList({ messages, isStreaming }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  return (
    <div className="flex-1 overflow-y-auto py-6">
      <div className="max-w-3xl mx-auto px-6 space-y-3">
      {messages.length === 0 && !isStreaming && (
        <motion.div
          className="flex flex-col items-center justify-center h-full text-center gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.5 }}
          transition={{ delay: 0.3 }}
        >
          <p className="text-gray-500 text-sm">Start a conversation with Cleo, your AI Sales Coach</p>
        </motion.div>
      )}
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <AnimatePresence>
        {isStreaming && <TypingDots />}
      </AnimatePresence>
      <div ref={endRef} />
      </div>
    </div>
  );
}

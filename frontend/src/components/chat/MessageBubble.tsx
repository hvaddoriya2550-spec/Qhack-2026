import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import { motion } from "framer-motion";
import { User, Bot } from "lucide-react";
import type { Message } from "../../types/chat";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <motion.div
      className={clsx("flex gap-3", isUser ? "justify-end" : "justify-start")}
      initial={{ opacity: 0, x: isUser ? 20 : -20, y: 5 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      {/* Agent avatar */}
      {!isUser && (
        <motion.div
          className="w-8 h-8 rounded-full bg-gradient-to-br from-[#3535F3] to-[#5252F5] flex items-center justify-center flex-shrink-0 mt-1 shadow-lg shadow-[#3535F3]/20"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 15, delay: 0.1 }}
        >
          <Bot className="w-4 h-4 text-white" />
        </motion.div>
      )}

      <div className={clsx("max-w-[75%] flex flex-col gap-1")}>
        {/* Sender label */}
        {!isUser && (
          <motion.div
            className="mb-0.5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <span className="text-[11px] font-semibold text-[#3535F3]">Cleo</span>
          </motion.div>
        )}

        {/* Bubble */}
        <div
          className={clsx(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "bg-gradient-to-r from-[#3535F3] to-[#2828D0] text-white rounded-br-md"
              : "bg-white text-gray-800 border border-gray-200 shadow-sm rounded-bl-md",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none [&>p]:mb-2 [&>p:last-child]:mb-0 [&>ul]:mb-2 [&>ol]:mb-2">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>

      {/* User avatar */}
      {isUser && (
        <motion.div
          className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center flex-shrink-0 mt-1"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 15, delay: 0.1 }}
        >
          <User className="w-4 h-4 text-gray-500" />
        </motion.div>
      )}
    </motion.div>
  );
}

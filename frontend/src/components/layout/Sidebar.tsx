import { Link, useLocation } from "react-router-dom";
import { FolderOpen, MessageSquare, LayoutDashboard } from "lucide-react";
import clsx from "clsx";
import { useChatStore } from "../../store/chatStore";

export default function Sidebar() {
  const conversations = useChatStore((s) => s.conversations);
  const location = useLocation();

  return (
    <aside className="w-64 border-r border-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-800">
        <Link to="/" className="text-lg font-bold hover:text-blue-400 transition">
          Sales Agent
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        <SidebarLink
          to="/"
          icon={<LayoutDashboard className="w-4 h-4" />}
          label="Dashboard"
          active={location.pathname === "/"}
        />
        <SidebarLink
          to="/form"
          icon={<FolderOpen className="w-4 h-4" />}
          label="Leads"
          active={location.pathname === "/form"}
        />
        <SidebarLink
          to="/projects"
          icon={<FolderOpen className="w-4 h-4" />}
          label="Projects"
          active={location.pathname.startsWith("/projects")}
        />
        <SidebarLink
          to="/chat"
          icon={<MessageSquare className="w-4 h-4" />}
          label="Quick Chat"
          active={location.pathname === "/chat"}
        />

        {conversations.length > 0 && (
          <>
            <div className="text-xs text-gray-500 uppercase tracking-wide mt-4 mb-2 px-3">
              Recent Chats
            </div>
            {conversations.map((conv) => (
              <Link
                key={conv.id}
                to={`/chat/${conv.id}`}
                className="block px-3 py-2 rounded-lg hover:bg-gray-800 truncate text-sm text-gray-400"
              >
                {conv.title}
              </Link>
            ))}
          </>
        )}
      </nav>
    </aside>
  );
}

function SidebarLink({
  to,
  icon,
  label,
  active,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  active: boolean;
}) {
  return (
    <Link
      to={to}
      className={clsx(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition",
        active ? "bg-gray-800 text-white" : "text-gray-400 hover:bg-gray-800 hover:text-white",
      )}
    >
      {icon}
      {label}
    </Link>
  );
}

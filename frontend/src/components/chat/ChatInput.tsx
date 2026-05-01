import { useEffect, useRef, useState, type FormEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, Check, Loader2, File, Upload, X } from "lucide-react";

interface VaultDoc {
  filename: string;
  chars: number;
  uploaded_at?: string;
}

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
  projectId?: string;
}

export default function ChatInput({ onSend, disabled, projectId }: Props) {
  const [input, setInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [autoProjectId, setAutoProjectId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Vault popover state
  const [vaultOpen, setVaultOpen] = useState(false);
  const [vaultDocs, setVaultDocs] = useState<VaultDoc[]>([]);
  const [loadingVault, setLoadingVault] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  const effectiveProjectId = projectId || autoProjectId;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  const ensureProjectForUpload = async (): Promise<string> => {
    if (effectiveProjectId) return effectiveProjectId;
    const res = await fetch(
      `${import.meta.env.VITE_API_URL || ""}/api/v1/projects/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "New Lead" }),
      },
    );
    const project = await res.json();
    setAutoProjectId(project.id);
    return project.id;
  };

  // Fetch vault docs when popover opens
  useEffect(() => {
    if (!vaultOpen || !effectiveProjectId) return;
    setLoadingVault(true);
    fetch(`${import.meta.env.VITE_API_URL || ""}/api/v1/documents/${effectiveProjectId}`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setVaultDocs(data);
      })
      .catch(() => {})
      .finally(() => setLoadingVault(false));
  }, [vaultOpen, effectiveProjectId]);

  // Close popover on outside click
  useEffect(() => {
    if (!vaultOpen) return;
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setVaultOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [vaultOpen]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadedFile(null);
    try {
      const pid = await ensureProjectForUpload();
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(
        `${import.meta.env.VITE_API_URL || ""}/api/v1/documents/upload/${pid}`,
        { method: "POST", body: formData },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Upload failed");
      } else {
        const data = await res.json();
        setUploadedFile(file.name);
        setTimeout(() => setUploadedFile(null), 4000);
        // Refresh vault list
        setVaultDocs((prev) => [
          ...prev,
          { filename: data.filename, chars: data.chars, uploaded_at: new Date().toISOString() },
        ]);
      }
    } catch {
      alert("Upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <form onSubmit={handleSubmit} className="shrink-0 p-4" style={{ background: "rgba(255,255,255,0.9)", backdropFilter: "blur(12px)", borderTop: "1px solid #e5e7eb" }}>
      {uploadedFile && (
        <div className="max-w-3xl mx-auto mb-2 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs" style={{ background: "rgba(53,53,243,0.06)", color: "#3535F3" }}>
          <Check className="w-3.5 h-3.5" />
          <span><strong>{uploadedFile}</strong> uploaded — Cleo will use it in research</span>
        </div>
      )}

      <div className="flex gap-2 items-center max-w-3xl mx-auto" style={{ position: "relative" }}>
        {/* Hidden file input */}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          className="hidden"
        />

        {/* Paperclip button — opens vault popover */}
        <motion.button
          type="button"
          onClick={() => setVaultOpen((v) => !v)}
          disabled={uploading || disabled}
          className="rounded-xl transition flex items-center justify-center disabled:opacity-30"
          style={{
            width: "42px",
            height: "42px",
            background: vaultOpen ? "rgba(53,53,243,0.08)" : "#f8f9fb",
            border: `1px solid ${vaultOpen ? "rgba(53,53,243,0.3)" : "#e5e7eb"}`,
            color: vaultOpen ? "#3535F3" : "#64748b",
            cursor: uploading ? "not-allowed" : "pointer",
            flexShrink: 0,
          }}
          whileHover={{ borderColor: "#3535F3", color: "#3535F3" }}
          whileTap={{ scale: 0.95 }}
          title="Documents vault"
        >
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
        </motion.button>

        {/* Vault popover */}
        <AnimatePresence>
          {vaultOpen && (
            <motion.div
              ref={popoverRef}
              initial={{ opacity: 0, y: 8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.15 }}
              style={{
                position: "absolute",
                bottom: "calc(100% + 8px)",
                left: 0,
                width: "320px",
                background: "#ffffff",
                borderRadius: "16px",
                border: "1px solid #e5e7eb",
                boxShadow: "0 12px 40px rgba(0,0,0,0.12)",
                zIndex: 50,
                overflow: "hidden",
              }}
            >
              {/* Header */}
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "14px 16px 10px",
                borderBottom: "1px solid #f1f5f9",
              }}>
                <div>
                  <p style={{ margin: 0, fontSize: "0.68rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#3535F3", fontWeight: 700 }}>
                    Document Vault
                  </p>
                  <p style={{ margin: "2px 0 0", fontSize: "0.82rem", fontWeight: 600, color: "#0f172a" }}>
                    {effectiveProjectId ? `${vaultDocs.length} file${vaultDocs.length !== 1 ? "s" : ""}` : "No project yet"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setVaultOpen(false)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8", padding: "4px" }}
                >
                  <X size={16} />
                </button>
              </div>

              {/* Doc list */}
              <div style={{ maxHeight: "180px", overflowY: "auto", padding: "8px 12px" }}>
                {loadingVault ? (
                  <div style={{ textAlign: "center", padding: "16px 0", color: "#94a3b8" }}>
                    <Loader2 size={16} style={{ animation: "spin 1s linear infinite", display: "inline-block" }} />
                  </div>
                ) : vaultDocs.length === 0 ? (
                  <p style={{ margin: 0, padding: "12px 0", color: "#94a3b8", fontSize: "0.82rem", textAlign: "center" }}>
                    No documents yet
                  </p>
                ) : (
                  vaultDocs.map((doc, i) => (
                    <div key={i} style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      padding: "8px 10px",
                      borderRadius: "10px",
                      background: "#f8f9fb",
                      marginBottom: i < vaultDocs.length - 1 ? "6px" : 0,
                    }}>
                      <File size={15} style={{ color: "#3535F3", flexShrink: 0 }} />
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <p style={{ margin: 0, fontSize: "0.8rem", fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {doc.filename}
                        </p>
                        <p style={{ margin: 0, fontSize: "0.68rem", color: "#94a3b8" }}>
                          {Math.round((doc.chars || 0) / 100) / 10}k chars
                        </p>
                      </div>
                      <Check size={14} style={{ color: "#22c55e", flexShrink: 0 }} />
                    </div>
                  ))
                )}
              </div>

              {/* Upload new button */}
              <div style={{ padding: "10px 12px", borderTop: "1px solid #f1f5f9" }}>
                <motion.button
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px",
                    padding: "10px",
                    borderRadius: "10px",
                    background: "#3535F3",
                    color: "#ffffff",
                    border: "none",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    cursor: uploading ? "not-allowed" : "pointer",
                  }}
                >
                  {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                  {uploading ? "Uploading..." : "Upload new PDF"}
                </motion.button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={disabled}
          className="flex-1 rounded-xl px-4 py-3 text-sm focus:outline-none transition-all duration-200"
          style={{
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            color: "#0f172a",
          }}
          onFocus={(e) => {
            e.target.style.borderColor = "rgba(53,53,243,0.5)";
            e.target.style.boxShadow = "0 0 0 3px rgba(53,53,243,0.1)";
          }}
          onBlur={(e) => {
            e.target.style.borderColor = "#e5e7eb";
            e.target.style.boxShadow = "none";
          }}
        />
        <motion.button
          type="submit"
          disabled={disabled || !input.trim()}
          className="rounded-xl text-sm font-medium disabled:opacity-30 transition flex items-center gap-1.5"
          style={{
            padding: "12px 20px",
            background: "#3535F3",
            color: "#fff",
            border: "none",
            cursor: disabled || !input.trim() ? "not-allowed" : "pointer",
          }}
          whileTap={{ scale: 0.9 }}
          whileHover={{ scale: 1.03 }}
        >
          <Send className="w-4 h-4" />
          Send
        </motion.button>
      </div>
    </form>
  );
}

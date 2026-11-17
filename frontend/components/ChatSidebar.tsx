"use client";

import React, { useState } from "react";
import { ChatSessionSummary, DocumentItem } from "@/types/chat";

interface ChatSidebarProps {
  chats: ChatSessionSummary[];
  activeChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onCreateNewChat: () => void;
  onDeleteChat: (chatId: string) => void;
  documents: DocumentItem[];
  onRemoveDoc: (docId: string) => void;
  onOpenUploadModal: () => void;
  isCreatingChat?: boolean;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  chats,
  activeChatId,
  onSelectChat,
  onCreateNewChat,
  onDeleteChat,
  documents,
  onRemoveDoc,
  onOpenUploadModal,
  isCreatingChat = false,
}) => {
  const [chatSearch, setChatSearch] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filteredChats = chats.filter((c) =>
    c.title.toLowerCase().includes(chatSearch.toLowerCase())
  );

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return "just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7) return `${diffDays}d ago`;
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch {
      return "";
    }
  };

  return (
    <aside className="w-72 border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0 h-full select-none">
      {/* Top Brand & New Chat */}
      <div className="p-4 border-b border-zinc-800 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white font-bold text-xs shadow-sm shadow-blue-500/20">
              IF
            </div>
            <span className="font-semibold text-zinc-100 text-sm tracking-tight">
              Intelligence Forge
            </span>
          </div>
          <span className="text-[10px] font-medium text-blue-400 bg-blue-950/60 border border-blue-800/40 px-1.5 py-0.5 rounded">
            GraphRAG
          </span>
        </div>

        <button
          onClick={onCreateNewChat}
          disabled={isCreatingChat}
          className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition shadow-sm cursor-pointer"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
          </svg>
          New Research Chat
        </button>
      </div>

      {/* Chat History List */}
      <div className="flex-1 flex flex-col min-h-0 border-b border-zinc-800/80">
        <div className="px-4 pt-3 pb-1 flex items-center justify-between text-[11px] font-medium text-zinc-400">
          <span>Conversations</span>
          <span className="text-zinc-600 font-mono text-[10px]">{chats.length}</span>
        </div>

        {chats.length > 5 && (
          <div className="px-3 py-1">
            <input
              type="text"
              placeholder="Filter chats..."
              value={chatSearch}
              onChange={(e) => setChatSearch(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800/80 rounded px-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
            />
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
          {filteredChats.length === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-zinc-500">
              {chatSearch ? "No matching chats" : "No conversations yet"}
            </div>
          ) : (
            filteredChats.map((c) => {
              const isActive = c.id === activeChatId;
              const isDeleting = deletingId === c.id;

              return (
                <div
                  key={c.id}
                  onClick={() => onSelectChat(c.id)}
                  className={`group relative flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition ${
                    isActive
                      ? "bg-zinc-800/90 text-zinc-100 font-medium"
                      : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                  }`}
                >
                  <div className="flex-1 min-w-0 pr-2">
                    <div className="truncate text-xs">{c.title || "Untitled Chat"}</div>
                    <div className="flex items-center gap-2 mt-0.5 text-[10px] text-zinc-500">
                      <span>{formatTime(c.updated_at)}</span>
                      {c.message_count > 0 && (
                        <span>• {c.message_count} msg</span>
                      )}
                      {c.doc_ids.length > 0 && (
                        <span className="text-blue-400">📎 {c.doc_ids.length}</span>
                      )}
                    </div>
                  </div>

                  {/* Delete button on hover */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeletingId(c.id);
                      onDeleteChat(c.id);
                    }}
                    title="Delete conversation"
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-zinc-500 rounded transition"
                  >
                    {isDeleting ? (
                      <span className="text-[10px] text-zinc-500">...</span>
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    )}
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Uploaded Papers Section (Bottom half) - Scoped to Active Chat */}
      <div className="h-64 flex flex-col shrink-0 bg-zinc-950">
        <div className="px-4 pt-3 pb-2 flex items-center justify-between text-[11px] font-medium text-zinc-400 border-t border-zinc-800/80">
          <div className="flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Chat Papers ({documents.length})</span>
          </div>
          <button
            onClick={onOpenUploadModal}
            className="text-blue-400 hover:text-blue-300 text-[10px] font-semibold flex items-center gap-1 cursor-pointer"
          >
            + Upload PDF
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
          {documents.length === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-zinc-500">
              No papers attached to this chat yet.<br />
              <button
                onClick={onOpenUploadModal}
                className="mt-2 text-blue-400 hover:underline text-[11px] cursor-pointer"
              >
                + Upload PDF to this chat
              </button>
            </div>
          ) : (
            documents.map((doc) => {
              const isReady = doc.extraction_status === "completed";

              return (
                <div
                  key={doc.doc_id}
                  title={doc.filename}
                  className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs bg-zinc-900/60 border border-zinc-800/60 text-zinc-300 hover:border-zinc-700 transition"
                >
                  <div className="flex items-center gap-2 min-w-0 pr-1">
                    <svg className="w-3.5 h-3.5 text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="truncate text-[11px] font-medium text-zinc-200">
                      {doc.filename}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {isReady ? (
                      <span className="text-[9px] bg-emerald-950 text-emerald-400 border border-emerald-800/50 px-1.5 py-0.5 rounded font-mono">
                        Ready
                      </span>
                    ) : (
                      <span className="text-[9px] bg-amber-950 text-amber-400 border border-amber-800/50 px-1.5 py-0.5 rounded font-mono">
                        {doc.extraction_status === "parsing" || doc.extraction_status === "extracting" ? "Processing" : doc.extraction_status}
                      </span>
                    )}
                    <button
                      onClick={() => onRemoveDoc(doc.doc_id)}
                      title="Detach paper from this chat"
                      className="p-1 hover:text-red-400 text-zinc-500 rounded transition cursor-pointer text-xs leading-none"
                    >
                      ×
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
};

"use client";

import React, { useEffect, useRef, useState } from "react";
import { ChatMessageBubble } from "./ChatMessageBubble";
import { ChatSessionDetail, DocumentItem } from "@/types/chat";
import { exportChatMarkdown } from "@/lib/api";

interface ChatWorkspaceProps {
  activeChat: ChatSessionDetail | null;
  documents: DocumentItem[];
  onRemoveDoc: (docId: string) => void;
  onSendMessage: (content: string, allowWebSearch?: boolean) => Promise<void>;
  isSending: boolean;
  onOpenUploadModal: () => void;
}

const STARTER_PROMPTS = [
  "Summarize the main contributions of my uploaded paper",
  "What methods and datasets are evaluated in the study?",
  "List the key experimental results and comparative metrics",
  "Explain the core architectural principles and findings",
];

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  activeChat,
  documents,
  onRemoveDoc,
  onSendMessage,
  isSending,
  onOpenUploadModal,
}) => {
  const [inputText, setInputText] = useState("");
  const [allowWebSearch, setAllowWebSearch] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleExportMarkdown = async () => {
    if (!activeChat?.id || !activeChat.messages || activeChat.messages.length === 0 || isExporting) {
      return;
    }
    try {
      setIsExporting(true);
      const { filename, content } = await exportChatMarkdown(activeChat.id);
      const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export chat session:", err);
    } finally {
      setIsExporting(false);
    }
  };

  // Auto-scroll to bottom on message update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeChat?.messages, isSending]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isSending) return;
    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    await onSendMessage(trimmed, allowWebSearch);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    // Auto-adjust height up to 160px
    const target = e.target;
    target.style.height = "auto";
    target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
  };

  return (
    <main className="flex-1 flex flex-col bg-[#09090b] min-w-0 h-full relative">
      {/* Top Header */}
      <header className="h-14 border-b border-zinc-800 px-6 flex items-center justify-between shrink-0 bg-zinc-950/80 backdrop-blur">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="text-sm font-semibold text-zinc-100 truncate max-w-sm">
            {activeChat?.title || "New Research Chat"}
          </h1>

          {/* Attached Document Badges */}
          <div className="hidden sm:flex items-center gap-1.5 overflow-x-auto py-1">
            {documents.length === 0 ? (
              <span className="text-[11px] text-zinc-500 italic">
                No papers attached to this chat
              </span>
            ) : (
              documents.map((doc) => (
                <span
                  key={doc.doc_id}
                  className="inline-flex items-center gap-1 bg-blue-950/60 border border-blue-800/60 text-blue-300 text-[11px] px-2 py-0.5 rounded-full font-medium"
                >
                  <span className="truncate max-w-[120px]">{doc.filename}</span>
                  <button
                    onClick={() => onRemoveDoc(doc.doc_id)}
                    className="hover:text-blue-100 p-0.5"
                    title="Detach from this chat"
                  >
                    ×
                  </button>
                </span>
              ))
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleExportMarkdown}
            disabled={!activeChat?.id || !activeChat.messages || activeChat.messages.length === 0 || isExporting}
            className="text-xs px-2.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-40 disabled:hover:bg-zinc-900 disabled:cursor-not-allowed border border-zinc-700/80 text-zinc-300 rounded-lg flex items-center gap-1.5 transition font-medium cursor-pointer"
            title={
              !activeChat?.id || !activeChat.messages || activeChat.messages.length === 0
                ? "Chat must have messages to export"
                : "Export session as Markdown report"
            }
          >
            <svg className="w-3.5 h-3.5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {isExporting ? "Exporting..." : "Export .md"}
          </button>

          <button
            onClick={onOpenUploadModal}
            className="text-xs px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/80 text-zinc-200 rounded-lg flex items-center gap-1.5 transition font-medium cursor-pointer"
          >
            <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Upload Paper
          </button>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
        {(!activeChat || activeChat.messages.length === 0) ? (
          /* Empty / Welcome State */
          <div className="max-w-2xl mx-auto my-auto pt-8 pb-12 flex flex-col items-center text-center">
            <div className="w-14 h-14 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-4 shadow-lg shadow-blue-500/5">
              <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>

            <h2 className="text-xl font-bold text-zinc-100 tracking-tight mb-2">
              GraphRAG Research Assistant
            </h2>
            <p className="text-sm text-zinc-400 max-w-md mb-6 leading-relaxed">
              Ask deep questions across your research literature. Answers are verified and strictly grounded in extracted knowledge graph entities and verbatim page citations.
            </p>

            {/* Quick Upload Drag-and-Drop Card if no docs */}
            {documents.length === 0 && (
              <div
                onClick={onOpenUploadModal}
                className="w-full max-w-md p-6 border-2 border-dashed border-zinc-800 hover:border-blue-500/60 bg-zinc-950/60 rounded-xl cursor-pointer transition mb-6 group"
              >
                <div className="text-blue-400 mx-auto w-8 h-8 mb-2 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div className="text-xs font-semibold text-zinc-200">
                  Upload PDF Research Papers
                </div>
                <div className="text-[11px] text-zinc-500 mt-0.5">
                  Drag and drop research papers here to extract entities & relationships
                </div>
              </div>
            )}

            {/* Clickable Starter Questions */}
            <div className="w-full max-w-lg grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
              {STARTER_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendMessage(prompt)}
                  disabled={isSending}
                  className="p-3 bg-zinc-900/80 hover:bg-zinc-850 hover:border-zinc-700 border border-zinc-800/80 rounded-xl text-xs text-zinc-300 transition text-left cursor-pointer flex flex-col justify-between group"
                >
                  <span className="leading-snug">{prompt}</span>
                  <span className="text-[10px] text-blue-400 mt-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    Ask question →
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message List */
          <div className="max-w-3xl mx-auto w-full">
            {activeChat.messages.map((msg) => (
              <ChatMessageBubble key={msg.id} message={msg} />
            ))}

            {/* Thinking / Searching Knowledge Base Indicator */}
            {isSending && (
              <div className="flex justify-start my-3">
                <div className="bg-zinc-900 border border-zinc-800 text-zinc-300 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse delay-150" />
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse delay-300" />
                  </div>
                  <span className="text-zinc-400">
                    Querying GraphRAG knowledge base & synthesizing grounded response...
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Bottom Composer Bar */}
      <div className="border-t border-zinc-800 bg-zinc-950/90 p-4 shrink-0 backdrop-blur">
        <div className="max-w-3xl mx-auto space-y-2">
          {/* Controls Bar */}
          <div className="flex items-center justify-between text-xs px-1">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setAllowWebSearch(!allowWebSearch)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border transition cursor-pointer ${
                  allowWebSearch
                    ? "bg-emerald-950/70 border-emerald-700/60 text-emerald-300 hover:bg-emerald-900/60"
                    : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
                title={
                  allowWebSearch
                    ? "DuckDuckGo fallback enabled if local papers lack coverage. Zero-leakage privacy firewall active."
                    : "Strictly local papers only. Outbound web search disabled."
                }
              >
                {allowWebSearch ? (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>Web Fallback: ON</span>
                    <span className="text-[10px] text-emerald-400/80 font-mono">(Privacy Shield Active)</span>
                  </>
                ) : (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
                    <span>Web Fallback: OFF</span>
                    <span className="text-[10px] text-zinc-500 font-mono">(Local Only)</span>
                  </>
                )}
              </button>
            </div>

            <span className="text-[11px] text-zinc-500 font-mono">
              Hybrid Vector + GraphRAG
            </span>
          </div>

          <div className="relative flex items-end gap-2 bg-zinc-900 border border-zinc-800 focus-within:border-blue-600/80 rounded-xl px-3 py-2 transition shadow-inner">
            {/* Attach PDF button */}
            <button
              onClick={onOpenUploadModal}
              title="Attach / Upload Research Paper"
              className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition mb-0.5 cursor-pointer"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </button>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputText}
              onChange={handleTextareaInput}
              onKeyDown={handleKeyDown}
              placeholder={
                documents.length > 0
                  ? `Ask anything about ${documents.length} attached paper${documents.length > 1 ? "s" : ""}... (Enter to send)`
                  : "Ask anything about your research papers... (Enter to send)"
              }
              className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none resize-none max-h-40 py-1"
            />

            {/* Send Button */}
            <button
              onClick={() => handleSubmit()}
              disabled={!inputText.trim() || isSending}
              className="p-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 text-white rounded-lg transition cursor-pointer mb-0.5"
              title="Send message"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </div>

        <div className="text-[10px] text-zinc-500 text-center mt-2">
          Responses are synthesized strictly from private paper extractions and knowledge graph provenance.
        </div>
      </div>
    </main>
  );
};

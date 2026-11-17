"use client";

import React, { useState } from "react";
import { ChatMessage, CitationItem, WebCitation } from "@/types/chat";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

export const ChatMessageBubble: React.FC<ChatMessageBubbleProps> = ({ message }) => {
  const isUser = message.role === "user";
  const [expandedCitationIndex, setExpandedCitationIndex] = useState<number | null>(null);
  const [expandedWebCitationIndex, setExpandedWebCitationIndex] = useState<number | null>(null);

  // Formatter for assistant responses (paragraphs, bold, code spans, lists, blockquotes)
  const renderFormattedContent = (content: string) => {
    const lines = content.split("\n");
    return (
      <div className="space-y-2 text-sm leading-relaxed">
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) {
            return <div key={idx} className="h-1.5" />;
          }

          // Headers
          if (trimmed.startsWith("### ")) {
            return (
              <h4 key={idx} className="font-bold text-zinc-100 text-sm mt-3 mb-1">
                {trimmed.replace("### ", "")}
              </h4>
            );
          }
          if (trimmed.startsWith("## ")) {
            return (
              <h3 key={idx} className="font-bold text-zinc-100 text-base mt-3 mb-1">
                {trimmed.replace("## ", "")}
              </h3>
            );
          }

          // Blockquotes
          if (trimmed.startsWith("> ")) {
            return (
              <blockquote
                key={idx}
                className="border-l-2 border-blue-500/80 bg-zinc-950/60 pl-3 py-1 my-1 text-zinc-300 italic text-xs rounded-r"
              >
                {trimmed.replace(/^>\s*/, "")}
              </blockquote>
            );
          }

          // Bullet list items
          if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
            const itemText = trimmed.replace(/^[-*]\s+/, "");
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="text-blue-400 mt-1.5 text-xs">•</span>
                <span className="flex-1">{renderInlineStyles(itemText)}</span>
              </div>
            );
          }

          // Standard paragraph
          return <p key={idx}>{renderInlineStyles(line)}</p>;
        })}
      </div>
    );
  };

  // Inline formatting helper for **bold**, `code`, and [citations]
  const renderInlineStyles = (text: string) => {
    // Split on bold tokens (**...**)
    const parts = text.split(/(\*\*.*?\*\*|`.*?`|\[.*?\])/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="font-semibold text-zinc-100">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={i}
            className="bg-zinc-800 text-blue-300 px-1 py-0.5 rounded font-mono text-xs"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith("[") && part.endsWith("]")) {
        return (
          <span
            key={i}
            className="inline-block text-[11px] font-mono font-medium text-blue-400 bg-blue-950/50 border border-blue-800/40 px-1.5 py-0.2 mx-0.5 rounded cursor-default"
          >
            {part}
          </span>
        );
      }
      return part;
    });
  };

  if (isUser) {
    return (
      <div className="flex justify-end my-3">
        <div className="max-w-[78%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 shadow-sm">
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  const agentTrace = message.agent_trace;
  const webCitations = message.web_citations || [];

  return (
    <div className="flex justify-start my-4">
      <div className="max-w-[88%] bg-zinc-900 border border-zinc-800/90 text-zinc-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-md space-y-3">
        {/* Assistant Header Badge & Routing Indicator */}
        <div className="flex items-center justify-between gap-2 pb-1.5 border-b border-zinc-800/50">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 text-xs font-bold">
              ⚡
            </div>
            <span className="text-xs font-medium text-zinc-300">Intelligence Forge Engine</span>
          </div>

          {/* Privacy & Dual-Agent Route Badge */}
          {agentTrace && (
            <div className="flex items-center gap-1.5">
              {agentTrace.web_agent_used ? (
                <span
                  title={`Web search fallback used with zero-leakage privacy firewall. Sanitized query: "${agentTrace.sanitized_query || ""}"`}
                  className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-950/60 text-emerald-300 border border-emerald-800/60"
                >
                  <svg className="w-2.5 h-2.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span>Dual-Agent · Privacy Verified</span>
                </span>
              ) : (
                <span
                  title="Answered purely from local vector embeddings & knowledge graph. Zero public queries sent."
                  className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-950/60 text-blue-300 border border-blue-800/60"
                >
                  <svg className="w-2.5 h-2.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <span>Local Grounded (Private)</span>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Message Content */}
        {renderFormattedContent(message.content)}

        {/* Local Sources & Citations Section */}
        {message.citations && message.citations.length > 0 && (
          <div className="pt-3 border-t border-zinc-800/70 mt-3">
            <div className="text-[11px] font-semibold text-zinc-400 mb-2 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <span>Verified Paper Passages ({message.citations.length})</span>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((cite: CitationItem, idx: number) => {
                const isExpanded = expandedCitationIndex === idx;
                const pageText = cite.page_number ? ` · p. ${cite.page_number}` : "";

                return (
                  <div key={idx} className="relative">
                    <button
                      onClick={() =>
                        setExpandedCitationIndex(isExpanded ? null : idx)
                      }
                      className={`text-[11px] font-mono px-2 py-1 rounded-md border flex items-center gap-1.5 transition cursor-pointer ${
                        isExpanded
                          ? "bg-blue-900/40 border-blue-600 text-blue-200"
                          : "bg-zinc-950 border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      <span>📄 {cite.filename}{pageText}</span>
                      <svg
                        className={`w-3 h-3 transform transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    {/* Expandable snippet popover / card */}
                    {isExpanded && (
                      <div className="mt-1.5 p-3 bg-zinc-950 border border-blue-800/60 rounded-lg text-xs text-zinc-300 max-w-md shadow-xl animate-in fade-in">
                        <div className="text-[10px] text-blue-400 font-semibold mb-1 flex items-center justify-between">
                          <span>Verified Passage Quote:</span>
                          <span>{cite.filename}{pageText}</span>
                        </div>
                        <p className="italic text-zinc-300 leading-relaxed border-l-2 border-blue-500 pl-2">
                          &ldquo;{cite.snippet}&rdquo;
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* External Web Citations (Agent 2 Fallback) */}
        {webCitations.length > 0 && (
          <div className="pt-3 border-t border-zinc-800/70 mt-3">
            <div className="text-[11px] font-semibold text-emerald-400 mb-2 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              <span>External Web Citations ({webCitations.length})</span>
            </div>

            <div className="space-y-1.5">
              {webCitations.map((web: WebCitation, idx: number) => {
                const isExpanded = expandedWebCitationIndex === idx;
                let domain = "";
                try {
                  domain = new URL(web.url).hostname.replace(/^www\./, "");
                } catch {
                  domain = "web";
                }

                return (
                  <div key={idx} className="bg-zinc-950/70 border border-zinc-800/80 rounded-lg p-2.5 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <a
                        href={web.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-emerald-300 hover:text-emerald-200 hover:underline flex items-center gap-1 truncate"
                      >
                        <span className="truncate">{web.title || domain}</span>
                        <svg className="w-3 h-3 shrink-0 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                      <span className="text-[10px] text-zinc-500 font-mono shrink-0">{domain}</span>
                    </div>

                    {web.snippet && (
                      <div className="mt-1">
                        <button
                          onClick={() => setExpandedWebCitationIndex(isExpanded ? null : idx)}
                          className="text-[10px] text-zinc-400 hover:text-zinc-200 cursor-pointer flex items-center gap-1"
                        >
                          <span>{isExpanded ? "Hide snippet" : "Show snippet"}</span>
                          <span className="text-[9px]">{isExpanded ? "▲" : "▼"}</span>
                        </button>
                        {isExpanded && (
                          <p className="mt-1.5 text-zinc-400 text-[11px] leading-relaxed bg-zinc-900/60 p-2 rounded border border-zinc-800">
                            {web.snippet}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ChatSidebar } from "@/components/ChatSidebar";
import { ChatWorkspace } from "@/components/ChatWorkspace";
import { UploadModal } from "@/components/UploadModal";
import {
  ChatSessionDetail,
  ChatSessionSummary,
  DocumentItem,
} from "@/types/chat";
import {
  createChat,
  deleteChat,
  fetchChatDetail,
  fetchChats,
  fetchDocuments,
  sendChatMessage,
  updateChatDocuments,
} from "@/lib/api";

export default function ResearchChatbotPage() {
  const [chats, setChats] = useState<ChatSessionSummary[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [activeChat, setActiveChat] = useState<ChatSessionDetail | null>(null);

  const [documents, setDocuments] = useState<DocumentItem[]>([]);

  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Load chat session detail and its scoped documents
  const loadChatDetail = useCallback(async (sessionId: string) => {
    // Reset documents immediately so papers from previous chat never flash
    setDocuments([]);
    try {
      const detail = await fetchChatDetail(sessionId);
      setActiveChat(detail);
      setActiveChatId(sessionId);
      const docs = await fetchDocuments(sessionId);
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load chat detail:", err);
    }
  }, []);

  // Load chat list
  const loadChats = useCallback(async (preferredSelectId?: string) => {
    try {
      const chatList = await fetchChats();
      setChats(chatList);

      if (preferredSelectId) {
        await loadChatDetail(preferredSelectId);
      } else if (chatList.length > 0) {
        await loadChatDetail(chatList[0].id);
      } else {
        // No chats yet: create initial chat session
        const newChat = await createChat("New Research Chat", []);
        setChats([
          {
            id: newChat.id,
            title: newChat.title,
            doc_ids: newChat.doc_ids,
            message_count: 0,
            updated_at: newChat.updated_at,
            created_at: newChat.created_at,
          },
        ]);
        setActiveChat(newChat);
        setActiveChatId(newChat.id);
        setDocuments([]);
      }
    } catch (err) {
      console.error("Failed to fetch chats:", err);
    }
  }, [loadChatDetail]);

  // Initial load
  useEffect(() => {
    let ignore = false;

    async function init() {
      try {
        const chatList = await fetchChats().catch(() => [] as ChatSessionSummary[]);
        if (ignore) return;
        setChats(chatList);

        if (chatList.length > 0) {
          const firstId = chatList[0].id;
          const detail = await fetchChatDetail(firstId).catch(() => null);
          if (ignore || !detail) return;
          setActiveChat(detail);
          setActiveChatId(firstId);
          const docs = await fetchDocuments(firstId).catch(() => [] as DocumentItem[]);
          if (ignore) return;
          setDocuments(docs);
        } else {
          const newChat = await createChat("New Research Chat", []).catch(() => null);
          if (ignore || !newChat) return;
          setChats([
            {
              id: newChat.id,
              title: newChat.title,
              doc_ids: newChat.doc_ids,
              message_count: 0,
              updated_at: newChat.updated_at,
              created_at: newChat.created_at,
            },
          ]);
          setActiveChat(newChat);
          setActiveChatId(newChat.id);
          setDocuments([]);
        }
      } catch (err) {
        console.error("Initialization error:", err);
      }
    }

    init();

    return () => {
      ignore = true;
    };
  }, []);

  // Create new chat
  const handleCreateNewChat = async () => {
    if (isCreatingChat) return;
    setIsCreatingChat(true);
    setDocuments([]); // Immediately reset documents for fresh chat
    try {
      const newChat = await createChat("New Research Chat", []);
      await loadChats(newChat.id);
    } catch (err) {
      console.error("Failed to create new chat:", err);
    } finally {
      setIsCreatingChat(false);
    }
  };

  // Delete chat
  const handleDeleteChat = async (sessionId: string) => {
    try {
      await deleteChat(sessionId);
      const remaining = chats.filter((c) => c.id !== sessionId);
      setChats(remaining);

      if (activeChatId === sessionId) {
        if (remaining.length > 0) {
          await loadChatDetail(remaining[0].id);
        } else {
          // If all deleted, create fresh one
          handleCreateNewChat();
        }
      }
    } catch (err) {
      console.error("Failed to delete chat:", err);
    }
  };

  // Remove paper attachment from active chat scope
  const handleRemoveDoc = async (docId: string) => {
    if (!activeChatId || !activeChat) return;
    const nextDocIds = (activeChat.doc_ids || []).filter((id) => id !== docId);

    try {
      await updateChatDocuments(activeChatId, nextDocIds);
      setActiveChat((prev) =>
        prev ? { ...prev, doc_ids: nextDocIds } : null
      );
      setChats((prev) =>
        prev.map((c) =>
          c.id === activeChatId ? { ...c, doc_ids: nextDocIds } : c
        )
      );
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
    } catch (err) {
      console.error("Failed to detach document from chat:", err);
    }
  };

  // Send message
  const handleSendMessage = async (content: string, allowWebSearch: boolean = true) => {
    if (!activeChatId || isSending) return;
    setIsSending(true);

    try {
      const docIds = activeChat?.doc_ids || [];
      const res = await sendChatMessage(activeChatId, content, docIds, allowWebSearch);

      // Append messages to active chat detail
      setActiveChat((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          title: res.session.title,
          updated_at: res.session.updated_at,
          messages: [...prev.messages, res.user_message, res.assistant_message],
        };
      });

      // Update sidebar session summary
      setChats((prev) =>
        prev.map((c) => (c.id === activeChatId ? res.session : c))
      );
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setIsSending(false);
    }
  };

  // Auto-poll document extraction status every 3000ms if any document is processing
  useEffect(() => {
    if (!activeChatId) return;

    const hasProcessingDocs = documents.some(
      (d) =>
        d.extraction_status === "uploaded" ||
        d.extraction_status === "queued" ||
        d.extraction_status === "parsing" ||
        d.extraction_status === "extracting"
    );

    if (!hasProcessingDocs) return;

    const interval = setInterval(async () => {
      try {
        const freshDocs = await fetchDocuments(activeChatId);
        setDocuments(freshDocs);
      } catch (err) {
        console.error("Auto-poll document error:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [activeChatId, documents]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-black text-zinc-100 font-sans">
      {/* Left Sidebar: Conversations & Scoped Papers */}
      <ChatSidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={(id) => loadChatDetail(id)}
        onCreateNewChat={handleCreateNewChat}
        onDeleteChat={handleDeleteChat}
        documents={documents}
        onRemoveDoc={handleRemoveDoc}
        onOpenUploadModal={() => setIsUploadModalOpen(true)}
        isCreatingChat={isCreatingChat}
      />

      {/* Main Center Stage: Chat Workspace */}
      <ChatWorkspace
        activeChat={activeChat}
        documents={documents}
        onRemoveDoc={handleRemoveDoc}
        onSendMessage={handleSendMessage}
        isSending={isSending}
        onOpenUploadModal={() => setIsUploadModalOpen(true)}
      />

      {/* Paper Ingestion Modal (Scoped strictly to activeChatId) */}
      <UploadModal
        isOpen={isUploadModalOpen}
        activeSessionId={activeChatId}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={async () => {
          if (activeChatId) {
            await loadChatDetail(activeChatId);
          }
        }}
      />
    </div>
  );
}

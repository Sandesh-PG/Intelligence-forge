from typing import Optional
from fastapi import APIRouter, HTTPException, Response, status

from app.core.config import settings
from app.schemas.chat import (
    ChatSessionDetail,
    ChatSessionSummary,
    CreateChatRequest,
    SendMessageRequest,
    SendMessageResponse,
    UpdateChatDocsRequest,
)
from app.services.chat_store import chat_store
from app.services.extraction_orchestrator import default_orchestrator as orchestrator
from app.services.graph_persistence_service import GraphPersistenceService
from app.services.graphrag_qa_service import GraphRAGQAService
from app.services.storage import delete_metadata, get_metadata

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("", response_model=list[ChatSessionSummary])
def list_chats() -> list[ChatSessionSummary]:
    """List all saved chat sessions ordered newest updated first."""
    return chat_store.list_sessions()


@router.post("", response_model=ChatSessionDetail, status_code=status.HTTP_201_CREATED)
def create_chat(payload: Optional[CreateChatRequest] = None) -> ChatSessionDetail:
    """Create a new chat session with optional title and attached document IDs."""
    title = payload.title if payload else "New Research Chat"
    doc_ids = payload.doc_ids if payload else []
    return chat_store.create_session(title=title, doc_ids=doc_ids)


@router.get("/{session_id}", response_model=ChatSessionDetail)
def get_chat(session_id: str) -> ChatSessionDetail:
    """Get full details and message history for a specific chat session."""
    session = chat_store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."},
        )
    return session


def _resolve_paper_filename(doc_id: str) -> str:
    """Resolve human-readable filename for a document ID from metadata stores."""
    status_item = orchestrator.metadata_store.get_status(doc_id)
    if status_item and status_item.original_filename:
        return status_item.original_filename
    meta = get_metadata(doc_id)
    if meta and meta.original_filename:
        return meta.original_filename
    return f"Paper-{doc_id[:8]}.pdf"


@router.get("/{session_id}/export")
def export_chat_markdown(session_id: str) -> Response:
    """Export the chat session as a clean Markdown report with verified citations."""
    session = chat_store.get_session_with_messages(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."},
        )

    lines: list[str] = [
        f"# {session.title}",
        "",
        f"- **Session ID:** `{session.id}`",
        f"- **Created:** {session.created_at}",
        f"- **Last Updated:** {session.updated_at}",
        "",
        "### Attached Research Papers",
    ]

    if session.doc_ids:
        for doc_id in session.doc_ids:
            fname = _resolve_paper_filename(doc_id)
            lines.append(f"- **{fname}** (`{doc_id}`)")
    else:
        lines.append("- *No research papers attached.*")

    lines.append("")
    lines.append("---")
    lines.append("")

    for msg in session.messages:
        if msg.role == "user":
            lines.append("## User")
            lines.append("")
            lines.append(msg.content.strip())
            lines.append("")
        else:
            lines.append("## Intelligence Forge Assistant")
            lines.append("")
            lines.append(msg.content.strip())
            lines.append("")

            # Agent & Privacy verification summary
            trace = msg.agent_trace or {}
            local_used = "Yes" if trace.get("local_agent_used", True) else "No"
            web_used = "Yes" if trace.get("web_agent_used", False) else "No"
            priv_verified = "Yes" if trace.get("privacy_verified", True) else "No"

            lines.append(
                f"> **Verification & Trace:** Local Grounded: {local_used} | "
                f"Web Fallback: {web_used} | Privacy Verified: {priv_verified}"
            )
            lines.append("")

            # Local Paper Citations
            if msg.citations:
                lines.append("### Local Paper Citations")
                for c in msg.citations:
                    page_str = f", p. {c.page_number}" if c.page_number is not None else ""
                    lines.append(f"- [{c.filename}{page_str}]: \"{c.snippet.strip()}\"")
                lines.append("")

            # External Web Sources
            if msg.web_citations:
                lines.append("### External Web Sources")
                for wc in msg.web_citations:
                    lines.append(f"- [{wc.title}]({wc.url})")
                lines.append("")

        lines.append("---")
        lines.append("")

    markdown_text = "\n".join(lines)
    filename = f"research-session-{session_id[:8]}.md"

    return Response(
        content=markdown_text,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{session_id}/documents", response_model=ChatSessionSummary)
def update_chat_documents(session_id: str, payload: UpdateChatDocsRequest) -> ChatSessionSummary:
    """Update attached document IDs scoping the chat session."""
    updated = chat_store.update_session_docs(session_id, payload.doc_ids)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."},
        )
    return updated


@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
def delete_chat(session_id: str) -> dict[str, bool]:
    """Delete a chat session and cascade cleanup unreferenced documents."""
    session = chat_store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."},
        )

    deleted_doc_ids = list(session.doc_ids)

    deleted = chat_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."},
        )

    # Check which doc_ids are no longer referenced by any remaining chat session
    still_referenced = chat_store.get_all_referenced_doc_ids()
    unreferenced_docs = [d for d in deleted_doc_ids if d not in still_referenced]

    for doc_id in unreferenced_docs:
        # 1. Local raw PDF
        pdf_path = settings.upload_storage_dir / f"{doc_id}.pdf"
        if pdf_path.exists():
            try:
                pdf_path.unlink()
            except OSError:
                pass

        # 2. Extracted JSON
        json_path = settings.extracted_storage_dir / f"{doc_id}.json"
        if json_path.exists():
            try:
                json_path.unlink()
            except OSError:
                pass

        # 3. Metadata entries
        delete_metadata(doc_id)
        orchestrator.metadata_store.delete_status(doc_id)

        # 4. Neo4j graph nodes and relationships
        GraphPersistenceService.delete_document_graph(doc_id)

    return {"deleted": True}


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, payload: SendMessageRequest) -> SendMessageResponse:
    """
    Append a user message, run GraphRAG retrieval + Ollama synthesis,
    persist assistant message with citations, and return conversation update.
    """
    session = chat_store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."},
        )

    # Determine document scope
    effective_doc_ids = payload.doc_ids if payload.doc_ids is not None else session.doc_ids
    if payload.doc_ids is not None and payload.doc_ids != session.doc_ids:
        chat_store.update_session_docs(session_id, payload.doc_ids)

    # 1. Persist user message
    user_msg = chat_store.append_message(
        session_id=session_id,
        role="user",
        content=payload.content,
        citations=[],
        auto_title_from_first_user_msg=True,
    )

    # 2. Answer question using GraphRAG Q&A Engine (Dual-Agent + Privacy Firewall)
    answer_text, citations, web_citations, agent_trace = await GraphRAGQAService.answer_question(
        question=payload.content,
        doc_ids=effective_doc_ids,
        chat_history=session.messages,
        allow_web_search=payload.allow_web_search,
    )

    # 3. Persist assistant message with citations & trace
    assistant_msg = chat_store.append_message(
        session_id=session_id,
        role="assistant",
        content=answer_text,
        citations=citations,
        web_citations=web_citations,
        agent_trace=agent_trace,
    )

    # 4. Fetch updated session summary
    summaries = [s for s in chat_store.list_sessions() if s.id == session_id]
    if summaries:
        summary = summaries[0]
    else:
        summary = ChatSessionSummary(
            id=session.id,
            title=session.title,
            doc_ids=effective_doc_ids,
            message_count=len(session.messages) + 2,
            updated_at=assistant_msg.created_at,
            created_at=session.created_at,
        )

    return SendMessageResponse(
        session=summary,
        user_message=user_msg,
        assistant_message=assistant_msg,
    )

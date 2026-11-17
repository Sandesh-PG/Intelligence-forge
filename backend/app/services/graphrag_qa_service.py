import json
import logging
import re
from typing import Optional

import httpx

from app.core.config import settings
from app.schemas.chat import ChatMessageOut, CitationItem, WebCitation
from app.services.global_web_agent import GlobalWebAgent
from app.services.graph_persistence_service import GraphPersistenceService
from app.services.privacy_guard import PrivacyGuard

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were",
    "will", "with", "what", "which", "where", "when", "how", "who", "whom", "this",
    "these", "those", "their", "they", "we", "can", "could", "should", "would",
}


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", text.lower())
    return [w for w in words if w not in STOPWORDS]


class GraphRAGQAService:
    @staticmethod
    async def answer_question(
        question: str,
        doc_ids: Optional[list[str]] = None,
        chat_history: Optional[list[ChatMessageOut]] = None,
        allow_web_search: bool = True,
    ) -> tuple[str, list[CitationItem], list[WebCitation], dict]:
        """
        2-Agent Orchestration Workflow:
        1. Agent 1 (Local Grounded Agent):
           - Retrieves hybrid vector chunks + Neo4j graph facts strictly scoped to doc_ids.
           - Evaluates whether uploaded papers fully answer the question (COVERAGE: COMPLETE vs COVERAGE: INSUFFICIENT).
        2. Privacy Firewall + Agent 2 (Global Web Agent):
           - Triggered ONLY when COVERAGE is INSUFFICIENT (or no docs attached) AND allow_web_search is True.
           - Sanitizes public query through PrivacyGuard (stripping filenames, IDs, 4-word verbatim spans).
           - Queries DuckDuckGo and synthesizes external context.
           - Distinguishes 'From Uploaded Research Papers' and 'External Web Context'.
        """
        scoped_doc_ids = [d for d in (doc_ids or []) if d]
        keywords = extract_keywords(question)
        citations: list[CitationItem] = []
        seen_citation_keys: set[str] = set()

        recent_history = (chat_history or [])[-6:]
        history_messages = [
            {
                "role": "user" if msg.role == "user" else "assistant",
                "content": msg.content,
            }
            for msg in recent_history
        ]

        # Case 0: No documents attached to this chat session
        if not scoped_doc_ids:
            greeting_phrases = {"hello", "hi", "hey", "greetings", "good morning", "good evening", "help", "who are you", "what can you do"}
            is_greeting = question.strip().lower().rstrip("!?., ") in greeting_phrases or len(keywords) == 0

            if not is_greeting and allow_web_search and settings.enable_global_web_agent:
                # Run privacy guard (even with no local papers, sanitizes PII/system tokens)
                privacy_res = PrivacyGuard.sanitize_for_public_web(
                    user_question=question,
                    missing_concepts=[],
                    local_chunks=[],
                    local_filenames=[],
                )
                if privacy_res.is_safe and privacy_res.sanitized_query:
                    web_summary, web_citations = await GlobalWebAgent.search_and_synthesize(
                        sanitized_query=privacy_res.sanitized_query,
                        user_question=question,
                    )
                    if web_summary:
                        ans = (
                            f"### External Web Context\n{web_summary}\n\n"
                            f"*(Note: No research papers are attached to this chat session. "
                            f"This context was retrieved from the public web via Privacy Firewall.)*"
                        )
                        trace = {
                            "local_agent_used": False,
                            "web_agent_used": True,
                            "privacy_verified": True,
                            "sanitized_query": privacy_res.sanitized_query,
                            "redacted_count": len(privacy_res.redacted_terms),
                        }
                        return ans, [], web_citations, trace

            # Default friendly no-docs message
            welcome_msg = (
                "Hello! No research papers are attached to this chat session yet. "
                "Please attach one or more research papers (PDF) using the paperclip button "
                "or upload modal so I can analyze them and answer your questions."
            )
            trace = {
                "local_agent_used": False,
                "web_agent_used": False,
                "privacy_verified": True,
                "sanitized_query": None,
                "redacted_count": 0,
            }
            return welcome_msg, [], [], trace

        # --- STEP 1: Agent 1 (Local Grounded Retrieval) ---
        hybrid_res = await GraphPersistenceService.retrieve_hybrid_context(
            question=question,
            doc_ids=scoped_doc_ids,
            top_k=8,
        )

        retrieved_chunks = hybrid_res.get("chunks", [])
        retrieved_entities = hybrid_res.get("entities", [])
        retrieved_relationships = hybrid_res.get("relationships", [])

        local_chunk_texts: list[str] = []
        local_filenames_set: set[str] = set()

        for c in retrieved_chunks:
            local_chunk_texts.append(c["text"])
            fname = c.get("filename") or f"{c['doc_id']}.pdf"
            local_filenames_set.add(fname)
            cite_key = f"{c['doc_id']}_{c['page_number']}_{c['text'][:60]}"
            if cite_key not in seen_citation_keys:
                seen_citation_keys.add(cite_key)
                citations.append(
                    CitationItem(
                        doc_id=c["doc_id"],
                        filename=fname,
                        page_number=c["page_number"],
                        snippet=c["text"][:300],
                    )
                )

        local_filenames = list(local_filenames_set)

        # Build local context prompt block
        context_blocks: list[str] = []
        if retrieved_chunks:
            context_blocks.append("### Relevant Passages from Uploaded Papers:")
            for c in retrieved_chunks[:6]:
                context_blocks.append(
                    f"[{c['filename']}, Page {c['page_number']}]:\n\"{c['text']}\""
                )

        if retrieved_entities:
            context_blocks.append("\n### Key Graph Entities:")
            for e in retrieved_entities[:6]:
                desc = f" ({e['description']})" if e.get("description") else ""
                context_blocks.append(f"- **{e['name']}** [{', '.join(e.get('labels', ['Entity']))}]{desc}")

        if retrieved_relationships:
            context_blocks.append("\n### Verified Relationship Facts & Evidence:")
            for r in retrieved_relationships[:6]:
                ev_str = f" | Evidence: \"{r['evidence']}\"" if r.get("evidence") else ""
                context_blocks.append(f"- {r['source']} -> {r['type']} -> {r['target']} [p. {r.get('page_number', 1)}]{ev_str}")

        combined_local_context = "\n\n".join(context_blocks).strip()

        # Prompt for Agent 1 with strict grounding and coverage tag requirement
        agent1_system_prompt = (
            "You are an expert academic research assistant powered by a GraphRAG knowledge engine.\n"
            "Answer the user's question accurately, strictly grounding your response in the provided paper passages and knowledge graph facts.\n"
            "Whenever stating a finding or claim, cite the source inline in [Filename, p. X] format.\n"
            "At the very end of your response, on a completely new line, evaluate the coverage of the uploaded papers for this question:\n"
            "- Write 'COVERAGE: COMPLETE' if the provided paper context completely answers the user's question.\n"
            "- Write 'COVERAGE: INSUFFICIENT | MISSING: <short abstract missing concept>' if the provided papers lack information needed to answer the question."
        )

        agent1_user_content = (
            f"Retrieved Document Context:\n{combined_local_context}\n\n"
            f"User Question:\n{question}"
        )

        agent1_messages = [
            {"role": "system", "content": agent1_system_prompt},
            *history_messages,
            {"role": "user", "content": agent1_user_content},
        ]

        agent1_response_text = ""
        coverage_status = "COMPLETE"
        missing_topic = ""

        # Call Ollama for Agent 1 with fast connect timeout so offline fallbacks are instant
        timeout_cfg = httpx.Timeout(min(settings.ollama_timeout_seconds, 45.0), connect=0.5)
        try:
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                res = await client.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                    json={
                        "model": settings.ollama_model,
                        "messages": agent1_messages,
                        "stream": False,
                        "options": {"temperature": settings.ollama_temperature},
                    },
                )
                if res.status_code == 200:
                    resp_data = res.json()
                    raw_content = resp_data.get("message", {}).get("content", "").strip()
                    if raw_content:
                        # Parse coverage indicator
                        coverage_match = re.search(
                            r"COVERAGE:\s*(COMPLETE|INSUFFICIENT)(?:\s*\|\s*MISSING:\s*([^\n\r]+))?",
                            raw_content,
                            flags=re.IGNORECASE,
                        )
                        if coverage_match:
                            cov_type = coverage_match.group(1).upper()
                            coverage_status = "INSUFFICIENT" if "INSUFFICIENT" in cov_type else "COMPLETE"
                            missing_topic = (coverage_match.group(2) or "").strip()
                            clean_text = re.sub(
                                r"\n*COVERAGE:\s*(COMPLETE|INSUFFICIENT)(?:\s*\|\s*MISSING:\s*[^\n\r]+)?\s*$",
                                "",
                                raw_content,
                                flags=re.IGNORECASE,
                            ).strip()
                            agent1_response_text = clean_text
                        else:
                            agent1_response_text = raw_content
        except Exception as exc:
            logger.info("Ollama call for Agent 1 failed or offline (%s). Using direct synthesis.", exc)

        # Fallback offline synthesis for Agent 1 if Ollama didn't reply
        if not agent1_response_text:
            if retrieved_chunks:
                parts = ["Based on the retrieved research evidence from your documents:\n"]
                for c in retrieved_chunks[:3]:
                    parts.append(f"**From {c['filename']} (Page {c['page_number']}):**\n\"{c['text']}\"\n")
                if retrieved_entities:
                    parts.append("**Key Relevant Entities:**")
                    for ent in retrieved_entities[:4]:
                        desc = f" — {ent['description']}" if ent.get("description") else ""
                        parts.append(f"- **{ent['name']}**{desc}")
                agent1_response_text = "\n".join(parts)
                # Check if question keywords match the retrieved chunks
                matched_kw = sum(1 for kw in keywords if any(kw in c["text"].lower() for c in retrieved_chunks))
                if matched_kw >= max(1, len(keywords) // 2):
                    coverage_status = "COMPLETE"
                else:
                    coverage_status = "INSUFFICIENT"
                    missing_topic = " ".join([kw for kw in keywords if not any(kw in c["text"].lower() for c in retrieved_chunks)])
            else:
                agent1_response_text = "No relevant context found in the uploaded research papers for this question."
                coverage_status = "INSUFFICIENT"
                missing_topic = question

        # --- STEP 2: Zero-Leakage Privacy Firewall + Agent 2 (Global Web Agent) ---
        if coverage_status == "INSUFFICIENT" and allow_web_search and settings.enable_global_web_agent:
            # 1. Sanitize candidate query via PrivacyGuard
            privacy_res = PrivacyGuard.sanitize_for_public_web(
                user_question=question,
                missing_concepts=[missing_topic] if missing_topic else [],
                local_chunks=local_chunk_texts,
                local_filenames=local_filenames,
            )

            if privacy_res.is_safe and privacy_res.sanitized_query:
                # 2. Query Agent 2 exclusively using sanitized_query
                web_summary, web_citations = await GlobalWebAgent.search_and_synthesize(
                    sanitized_query=privacy_res.sanitized_query,
                    user_question=question,
                )

                if web_summary:
                    # Format dual-agent answer
                    combined_answer = (
                        f"### From Uploaded Research Papers\n{agent1_response_text}\n\n"
                        f"### External Web Context\n{web_summary}"
                    )
                    trace = {
                        "local_agent_used": True,
                        "web_agent_used": True,
                        "privacy_verified": True,
                        "sanitized_query": privacy_res.sanitized_query,
                        "redacted_count": len(privacy_res.redacted_terms),
                    }
                    return combined_answer, citations[:8], web_citations, trace
                else:
                    trace = {
                        "local_agent_used": True,
                        "web_agent_used": False,
                        "privacy_verified": True,
                        "sanitized_query": privacy_res.sanitized_query,
                        "redacted_count": len(privacy_res.redacted_terms),
                    }
                    return agent1_response_text, citations[:8], [], trace
            else:
                # Blocked by Privacy Firewall
                blocked_note = f"\n\n*(Web search fallback blocked by Privacy Firewall: {privacy_res.blocked_reason})*"
                trace = {
                    "local_agent_used": True,
                    "web_agent_used": False,
                    "privacy_verified": False,
                    "sanitized_query": None,
                    "redacted_count": len(privacy_res.redacted_terms),
                    "blocked_reason": privacy_res.blocked_reason,
                }
                return agent1_response_text + blocked_note, citations[:8], [], trace

        # Default Agent 1 complete response (Local Only)
        trace = {
            "local_agent_used": True,
            "web_agent_used": False,
            "privacy_verified": True,
            "sanitized_query": None,
            "redacted_count": 0,
        }
        return agent1_response_text, citations[:8], [], trace

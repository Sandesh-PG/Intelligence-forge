import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.schemas.chat import (
    ChatMessageOut,
    ChatSessionDetail,
    ChatSessionSummary,
    CitationItem,
    WebCitation,
)


class ChatStore:
    def __init__(self, db_path: Optional[Path] = None):
        self._custom_db_path = db_path

    @property
    def db_path(self) -> Path:
        if self._custom_db_path is not None:
            return self._custom_db_path
        return settings.data_dir / "chats.db"

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    doc_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    web_citations_json TEXT DEFAULT '[]',
                    agent_trace_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                );
                """
            )
            # Check existing columns using PRAGMA to safely migrate schema without throwing SQLite errors
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(chat_messages);").fetchall()}
            if "web_citations_json" not in cols:
                conn.execute("ALTER TABLE chat_messages ADD COLUMN web_citations_json TEXT DEFAULT '[]';")
            if "agent_trace_json" not in cols:
                conn.execute("ALTER TABLE chat_messages ADD COLUMN agent_trace_json TEXT DEFAULT '{}';")
            conn.commit()

    def create_session(self, title: Optional[str] = None, doc_ids: Optional[list[str]] = None) -> ChatSessionDetail:
        self.init_db()
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        session_title = (title or "New Research Chat").strip()
        doc_ids_clean = doc_ids or []

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, title, doc_ids_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (session_id, session_title, json.dumps(doc_ids_clean), now, now),
            )
            conn.commit()

        return ChatSessionDetail(
            id=session_id,
            title=session_title,
            doc_ids=doc_ids_clean,
            messages=[],
            updated_at=now,
            created_at=now,
        )

    def list_sessions(self) -> list[ChatSessionSummary]:
        self.init_db()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT 
                    s.id,
                    s.title,
                    s.doc_ids_json,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id) AS message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC;
                """
            )
            rows = cursor.fetchall()

        summaries = []
        for r in rows:
            try:
                doc_ids = json.loads(r["doc_ids_json"])
            except Exception:
                doc_ids = []
            summaries.append(
                ChatSessionSummary(
                    id=r["id"],
                    title=r["title"],
                    doc_ids=doc_ids,
                    message_count=r["message_count"],
                    updated_at=r["updated_at"],
                    created_at=r["created_at"],
                )
            )
        return summaries

    def get_session(self, session_id: str) -> Optional[ChatSessionDetail]:
        self.init_db()
        with self._get_connection() as conn:
            s_cur = conn.execute(
                "SELECT id, title, doc_ids_json, created_at, updated_at FROM chat_sessions WHERE id = ?;",
                (session_id,),
            )
            s_row = s_cur.fetchone()
            if not s_row:
                return None

            m_cur = conn.execute(
                """
                SELECT id, session_id, role, content, citations_json, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC, rowid ASC;
                """,
                (session_id,),
            )
            m_rows = m_cur.fetchall()

        try:
            doc_ids = json.loads(s_row["doc_ids_json"])
        except Exception:
            doc_ids = []

        messages: list[ChatMessageOut] = []
        for mr in m_rows:
            citations_raw = []
            try:
                citations_raw = json.loads(mr["citations_json"])
            except Exception:
                citations_raw = []
            citations = [CitationItem(**c) for c in citations_raw]

            web_citations_raw = []
            try:
                if "web_citations_json" in mr.keys() and mr["web_citations_json"]:
                    web_citations_raw = json.loads(mr["web_citations_json"])
            except Exception:
                web_citations_raw = []
            web_citations = [WebCitation(**wc) for wc in web_citations_raw]

            agent_trace = None
            try:
                if "agent_trace_json" in mr.keys() and mr["agent_trace_json"]:
                    agent_trace = json.loads(mr["agent_trace_json"])
            except Exception:
                agent_trace = None

            messages.append(
                ChatMessageOut(
                    id=mr["id"],
                    session_id=mr["session_id"],
                    role=mr["role"],
                    content=mr["content"],
                    citations=citations,
                    web_citations=web_citations,
                    agent_trace=agent_trace,
                    created_at=mr["created_at"],
                )
            )

        return ChatSessionDetail(
            id=s_row["id"],
            title=s_row["title"],
            doc_ids=doc_ids,
            messages=messages,
            updated_at=s_row["updated_at"],
            created_at=s_row["created_at"],
        )

    def get_session_with_messages(self, session_id: str) -> Optional[ChatSessionDetail]:
        """Fetch full chat session detail including all historical messages and citations."""
        return self.get_session(session_id)

    def update_session_docs(self, session_id: str, doc_ids: list[str]) -> Optional[ChatSessionSummary]:
        self.init_db()
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                UPDATE chat_sessions
                SET doc_ids_json = ?, updated_at = ?
                WHERE id = ?;
                """,
                (json.dumps(doc_ids), now, session_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None

            cnt_cur = conn.execute("SELECT COUNT(*) AS c FROM chat_messages WHERE session_id = ?;", (session_id,))
            msg_count = cnt_cur.fetchone()["c"]

            s_cur = conn.execute(
                "SELECT id, title, doc_ids_json, created_at, updated_at FROM chat_sessions WHERE id = ?;",
                (session_id,),
            )
            row = s_cur.fetchone()

        return ChatSessionSummary(
            id=row["id"],
            title=row["title"],
            doc_ids=doc_ids,
            message_count=msg_count,
            updated_at=row["updated_at"],
            created_at=row["created_at"],
        )

    def delete_session(self, session_id: str) -> bool:
        self.init_db()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?;", (session_id,))
            cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?;", (session_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_all_referenced_doc_ids(self) -> set[str]:
        """Return the set of all document IDs currently attached to any active chat session."""
        self.init_db()
        with self._get_connection() as conn:
            cur = conn.execute("SELECT doc_ids_json FROM chat_sessions;")
            rows = cur.fetchall()
        referenced: set[str] = set()
        for r in rows:
            try:
                ids = json.loads(r["doc_ids_json"])
                if isinstance(ids, list):
                    referenced.update(ids)
            except Exception:
                pass
        return referenced

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[list[CitationItem]] = None,
        web_citations: Optional[list[WebCitation]] = None,
        agent_trace: Optional[dict] = None,
        auto_title_from_first_user_msg: bool = False,
    ) -> ChatMessageOut:
        self.init_db()
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        citations_list = citations or []
        web_citations_list = [
            wc if isinstance(wc, WebCitation) else WebCitation(**wc)
            for wc in (web_citations or [])
        ]
        citations_json = json.dumps([c.model_dump() for c in citations_list])
        web_citations_json = json.dumps([wc.model_dump() for wc in web_citations_list])
        agent_trace_json = json.dumps(agent_trace or {})

        with self._get_connection() as conn:
            # Check existing messages count and title if auto-title requested
            if auto_title_from_first_user_msg and role == "user":
                cnt_cur = conn.execute(
                    "SELECT COUNT(*) AS c FROM chat_messages WHERE session_id = ?;",
                    (session_id,),
                )
                existing_count = cnt_cur.fetchone()["c"]
                if existing_count == 0:
                    # Generate concise title from first message
                    clean_content = " ".join(content.strip().split())
                    new_title = clean_content[:45] + ("..." if len(clean_content) > 45 else "")
                    conn.execute(
                        "UPDATE chat_sessions SET title = ? WHERE id = ? AND (title = 'New Research Chat' OR title = '');",
                        (new_title, session_id),
                    )

            conn.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, citations_json, web_citations_json, agent_trace_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (msg_id, session_id, role, content, citations_json, web_citations_json, agent_trace_json, now),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?;",
                (now, session_id),
            )
            conn.commit()

        return ChatMessageOut(
            id=msg_id,
            session_id=session_id,
            role=role,
            content=content,
            citations=citations_list,
            web_citations=web_citations_list,
            agent_trace=agent_trace,
            created_at=now,
        )


chat_store = ChatStore()

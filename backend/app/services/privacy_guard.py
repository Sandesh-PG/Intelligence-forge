import re
from typing import Optional
from pydantic import BaseModel, Field


class PrivacyCheckResult(BaseModel):
    sanitized_query: str
    is_safe: bool
    redacted_terms: list[str] = Field(default_factory=list)
    blocked_reason: Optional[str] = None


class PrivacyGuard:
    @staticmethod
    def _extract_words(text: str) -> list[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [w.strip() for w in cleaned.split() if w.strip()]

    @classmethod
    def _extract_4grams(cls, text: str) -> set[tuple[str, str, str, str]]:
        words = cls._extract_words(text)
        if len(words) < 4:
            return set()
        return {tuple(words[i : i + 4]) for i in range(len(words) - 3)}

    @classmethod
    def sanitize_for_public_web(
        cls,
        user_question: str,
        missing_concepts: list[str] | None = None,
        local_chunks: list[str] | None = None,
        local_filenames: list[str] | None = None,
    ) -> PrivacyCheckResult:
        redacted_terms: list[str] = []
        chunks = local_chunks or []
        filenames = local_filenames or []
        missing = [m.strip() for m in (missing_concepts or []) if m and m.strip()]

        # 1. Base candidate text: prioritize missing concepts, or user question
        if missing:
            candidate = " ".join(missing)
        else:
            candidate = user_question or ""

        # 2. Strip system / paper references
        boilerplate_patterns = [
            r"\b(in\s+this\s+paper|in\s+the\s+uploaded\s+paper|in\s+the\s+document|according\s+to\s+the\s+paper|from\s+the\s+pdf|in\s+pdf)\b",
            r"\b(uploaded\s+file|attached\s+paper|attached\s+document)\b",
        ]
        for pat in boilerplate_patterns:
            matches = re.findall(pat, candidate, flags=re.IGNORECASE)
            for m in matches:
                redacted_terms.append(m if isinstance(m, str) else m[0])
            candidate = re.sub(pat, " ", candidate, flags=re.IGNORECASE)

        # 3. Strip filenames (with and without .pdf extension) and identifiers
        for fn in filenames:
            if not fn:
                continue
            base_fn = re.sub(r"\.[a-zA-Z0-9]+$", "", fn).strip()
            patterns_to_strip = [re.escape(fn)]
            if len(base_fn) >= 3:
                patterns_to_strip.append(re.escape(base_fn))
            for pat in patterns_to_strip:
                if re.search(pat, candidate, flags=re.IGNORECASE):
                    redacted_terms.append(fn)
                    candidate = re.sub(pat, " ", candidate, flags=re.IGNORECASE)

        # 4. Strip emails, URLs, file paths, UUIDs
        leak_patterns = [
            (r"[\w\.-]+@[\w\.-]+\.\w+", "email"),
            (r"[A-Za-z]:\\[^\s]+", "file_path"),
            (r"/(?:[a-zA-Z0-9_\.-]+/)+[a-zA-Z0-9_\.-]+", "file_path"),
            (r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", "uuid"),
        ]
        for pat, desc in leak_patterns:
            found = re.findall(pat, candidate, flags=re.IGNORECASE)
            for f in found:
                redacted_terms.append(f)
            candidate = re.sub(pat, " ", candidate, flags=re.IGNORECASE)

        # 5. Extract 4-grams from local chunks
        forbidden_4grams: set[tuple[str, str, str, str]] = set()
        for chunk in chunks:
            forbidden_4grams.update(cls._extract_4grams(chunk))

        # Check and remove any 4-gram verbatim phrases from candidate
        cand_words = cls._extract_words(candidate)
        cleaned_words: list[str] = []
        i = 0
        while i < len(cand_words):
            if i + 3 < len(cand_words):
                quad = tuple(cand_words[i : i + 4])
                if quad in forbidden_4grams:
                    leak_phrase = " ".join(quad)
                    redacted_terms.append(leak_phrase)
                    # Skip the 4-gram words
                    i += 4
                    continue
            cleaned_words.append(cand_words[i])
            i += 1

        # 6. Build concise query (<= 12 words)
        final_words = cleaned_words[:12]
        sanitized_query = " ".join(final_words).strip()

        # 7. Final verification gate
        if len(sanitized_query) < 3:
            return PrivacyCheckResult(
                sanitized_query="",
                is_safe=False,
                redacted_terms=redacted_terms,
                blocked_reason="Blocked: candidate query was empty or under 3 characters after sanitization.",
            )

        # Final check if sanitized_query still shares any 4-gram with local_chunks
        query_4grams = cls._extract_4grams(sanitized_query)
        if query_4grams.intersection(forbidden_4grams):
            return PrivacyCheckResult(
                sanitized_query="",
                is_safe=False,
                redacted_terms=redacted_terms,
                blocked_reason="Blocked to prevent local document leakage (shares verbatim 4-word passage with local papers).",
            )

        return PrivacyCheckResult(
            sanitized_query=sanitized_query,
            is_safe=True,
            redacted_terms=redacted_terms,
            blocked_reason=None,
        )

import re
import urllib.parse
from typing import Optional
import httpx
from app.core.config import settings
from app.schemas.chat import WebCitation


class GlobalWebAgent:
    @staticmethod
    async def search_and_synthesize(
        sanitized_query: str,
        user_question: str = "",
    ) -> tuple[str, list[WebCitation]]:
        if not settings.enable_global_web_agent or not sanitized_query.strip():
            return ("", [])

        citations: list[WebCitation] = []
        encoded_query = urllib.parse.quote(sanitized_query.strip())

        try:
            timeout_cfg = httpx.Timeout(settings.web_search_timeout, connect=1.0)
            async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True) as client:
                # 1. Primary: DuckDuckGo Instant Answer API
                api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
                resp = await client.get(api_url, headers={"User-Agent": "IntelligenceForge/1.0"})
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        abstract = data.get("AbstractText", "").strip()
                        abstract_url = data.get("AbstractURL", "").strip()
                        abstract_source = data.get("AbstractSource", "").strip()
                        if abstract and abstract_url:
                            citations.append(
                                WebCitation(
                                    title=abstract_source or "DuckDuckGo Instant Answer",
                                    url=abstract_url,
                                    snippet=abstract,
                                )
                            )
                        related = data.get("RelatedTopics", [])
                        for item in related:
                            if isinstance(item, dict) and "Text" in item and "FirstURL" in item:
                                t = item.get("Text", "").strip()
                                u = item.get("FirstURL", "").strip()
                                if t and u:
                                    citations.append(
                                        WebCitation(
                                            title=t[:80] + ("..." if len(t) > 80 else ""),
                                            url=u,
                                            snippet=t,
                                        )
                                    )
                                if len(citations) >= 5:
                                    break
                    except Exception:
                        pass

                # 2. Secondary fallback if needed: HTML search
                if len(citations) < 2:
                    html_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                    html_resp = await client.get(
                        html_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                        },
                    )
                    if html_resp.status_code == 200:
                        html_text = html_resp.text
                        snippets = re.findall(
                            r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>',
                            html_text,
                            flags=re.DOTALL,
                        )
                        urls = re.findall(
                            r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                            html_text,
                            flags=re.DOTALL,
                        )
                        titles = re.findall(
                            r'<a class="result__title"[^>]*href="[^"]*"[^>]*>(.*?)</a>',
                            html_text,
                            flags=re.DOTALL,
                        )

                        for idx in range(min(len(snippets), 4)):
                            raw_snip = re.sub(r"<[^>]+>", "", snippets[idx]).strip()
                            raw_url = urls[idx][0].strip() if idx < len(urls) else ""
                            raw_title = (
                                re.sub(r"<[^>]+>", "", titles[idx]).strip()
                                if idx < len(titles)
                                else f"Web Result {idx + 1}"
                            )
                            if raw_snip:
                                actual_url = raw_url
                                if "uddg=" in actual_url:
                                    match = re.search(r"uddg=([^&]+)", actual_url)
                                    if match:
                                        actual_url = urllib.parse.unquote(match.group(1))
                                if not actual_url.startswith("http"):
                                    actual_url = f"https://duckduckgo.com/?q={encoded_query}"
                                citations.append(
                                    WebCitation(
                                        title=raw_title or f"Result {idx + 1}",
                                        url=actual_url,
                                        snippet=raw_snip,
                                    )
                                )
                                if len(citations) >= 5:
                                    break
        except Exception:
            pass

        if not citations:
            return ("", [])

        # Synthesize external summary
        context_snippets = "\n".join(f"- [{c.title}]({c.url}): {c.snippet}" for c in citations[:4])
        prompt = (
            f"You are a factual research assistant. Synthesize a concise external web summary answering: '{sanitized_query}'.\n"
            f"Use ONLY the following web search snippets:\n{context_snippets}\n\n"
            f"Provide a clear, direct summary in 2-3 sentences."
        )

        try:
            ollama_timeout = httpx.Timeout(min(settings.ollama_timeout_seconds, 15.0), connect=0.5)
            async with httpx.AsyncClient(timeout=ollama_timeout) as client:
                res = await client.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                    json={
                        "model": settings.ollama_model,
                        "messages": [
                            {"role": "system", "content": "You are a concise research synthesis agent."},
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                        "options": {"temperature": 0.0},
                    },
                )
                if res.status_code == 200:
                    body = res.json()
                    summary_text = body.get("message", {}).get("content", "").strip()
                    if summary_text:
                        return (summary_text, citations)
        except Exception:
            pass

        # Offline fallback: structured bulleted compilation
        fallback_summary = "\n".join(f"• **{c.title}**: {c.snippet}" for c in citations[:3])
        return (fallback_summary, citations)

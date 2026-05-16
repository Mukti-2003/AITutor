"""
scripts/query_data.py
======================
RAG query pipeline: retrieve → ground → generate.
Supports explanation modes, bilingual output, and analytics recording.
"""

import argparse
import logging
import os
import time
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from backend.llm_manager import get_embedding_function, get_fallback_llm
from backend.utils.prompt_modes import get_mode_prompt
from backend.analytics.progress_tracker import record_question

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHROMA_PATH = os.path.abspath(os.getenv("CHROMA_PATH", "chroma"))
DEFAULT_TOP_K     = int(os.getenv("RAG_TOP_K",            "5"))
MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "6000"))
MAX_CHUNK_CHARS   = int(os.getenv("RAG_MAX_CHUNK_CHARS",   "1200"))

RELEVANCE_DISTANCE_THRESHOLD = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "1.5"))

NO_CONTEXT_REPLY = (
    "I'm sorry, I could not find relevant information in the uploaded course "
    "materials to answer your question. Please make sure the relevant document "
    "has been uploaded and indexed, then try again."
)

PROMPT_TEMPLATE = """
You are an AI Teaching Assistant helping students understand academic material.

Answer ONLY using the provided context below. Do NOT use any prior knowledge.

IMPORTANT RULES:
- Base your answer STRICTLY on the context provided. If a fact is not in the
  context, do NOT include it.
- Use simple, student-friendly explanations.
- Use proper markdown formatting (headings, bullet points, bold, etc.).
- For mathematical formulas, use VALID LaTeX syntax wrapped in $$ ... $$.
- Never output broken LaTeX.
- Explain formulas in plain English after showing them.
- If the context does not contain enough information to answer the question,
  say: "The uploaded materials do not contain enough information to fully
  answer this question." Then explain what IS available.
- When possible, reference which part of the material the answer comes from.

Context:
{context}

---

Question:
{question}

Answer:
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_response_text(response) -> str:
    """Convert provider-specific response payloads into plain text."""
    content = getattr(response, "content", response)

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        joined = "\n".join([p for p in parts if p]).strip()
        if joined:
            return joined

    return str(content).strip()


def _fix_unicode_symbols(text: str) -> str:
    """Replace stray Unicode math symbols with proper LaTeX equivalents."""
    replacements = {
        "ŷ{y}": r"\hat{y}",
        "Σ": r"\sum",
        "λ": r"\lambda",
        "σ": r"\sigma",
        "μ": r"\mu",
        "α": r"\alpha",
        "β": r"\beta",
        "π": r"\pi",
        "∞": r"\infty",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


@lru_cache(maxsize=1)
def _get_db() -> Chroma:
    return Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embedding_function(),
    )


def _build_source_label(metadata: dict) -> str:
    """Build a human-readable source string from chunk metadata."""
    filename = metadata.get("filename") or metadata.get("source", "unknown")
    page = metadata.get("page")
    if page:
        return f"{filename} (page {page})"
    return str(filename)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def query_rag(query_text: str, mode: str = "default", language: str = "english") -> dict:
    """
    Run the full RAG pipeline for *query_text*.
    """
    t_start = time.perf_counter()
    db = _get_db()

    # 1. Retrieve top-k chunks
    try:
        results = db.similarity_search_with_score(query_text, k=DEFAULT_TOP_K)
        logger.info("Query: '%s' \u2192 %d candidate chunks retrieved", query_text[:80], len(results))
    except Exception as exc:
        logger.warning("ChromaDB search failed (possibly empty index): %s", exc)
        results = []

    # 2. Filter by relevance and build context budget
    selected_snippets = []
    selected_sources  = []
    source_details    = []
    current_len = 0

    for doc, distance in results:
        if distance > RELEVANCE_DISTANCE_THRESHOLD:
            continue

        snippet = (doc.page_content or "")[:MAX_CHUNK_CHARS].strip()
        if not snippet:
            continue

        projected = current_len + len(snippet) + 8
        if projected > MAX_CONTEXT_CHARS and selected_snippets:
            break

        selected_snippets.append(snippet)
        selected_sources.append(_build_source_label(doc.metadata))
        source_details.append({
            "filename": doc.metadata.get("filename", "unknown"),
            "page": doc.metadata.get("page"),
            "chunk_id": doc.metadata.get("id", ""),
            "subject": doc.metadata.get("subject", ""),
            "distance": round(distance, 4),
        })
        current_len = projected

    # 3. No-context guard
    if not selected_snippets:
        elapsed = (time.perf_counter() - t_start) * 1000
        return {
            "answer": NO_CONTEXT_REPLY,
            "sources": [],
            "source_details": [],
            "chunks_used": 0,
            "processing_time_ms": round(elapsed, 1),
            "context_text": ""
        }

    context_text = "\n\n---\n\n".join(selected_snippets)

    # 4. Build prompt + call LLM
    if mode and mode.lower() != "default" or language.lower() != "english":
        prompt = get_mode_prompt(mode, context_text, query_text, language)
    else:
        prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE).format(
            context=context_text,
            question=query_text,
        )
    
    llm = get_fallback_llm()
    try:
        response = llm.invoke(prompt)
    except Exception as exc:
        elapsed = (time.perf_counter() - t_start) * 1000
        return {
            "answer": f"The AI model could not generate a response. Error: {exc}",
            "sources": [],
            "source_details": source_details,
            "chunks_used": len(selected_snippets),
            "processing_time_ms": round(elapsed, 1),
            "context_text": context_text
        }
    
    response_text = _normalize_response_text(response)
    response_text = _fix_unicode_symbols(response_text)

    # Deduplicate sources
    seen = set()
    unique_sources = []
    for s in selected_sources:
        if s not in seen:
            unique_sources.append(s)
            seen.add(s)

    # 5. Record Analytics
    primary_topic = source_details[0]["subject"] if source_details else "unknown"
    record_question(query_text, primary_topic, unique_sources, mode or "default")

    elapsed = (time.perf_counter() - t_start) * 1000
    return {
        "answer": response_text,
        "sources": unique_sources,
        "source_details": source_details,
        "chunks_used": len(selected_snippets),
        "processing_time_ms": round(elapsed, 1),
        "context_text": context_text
    }


def main():
    parser = argparse.ArgumentParser(description="RAG query CLI")
    parser.add_argument("query_text", type=str, help="The query text.")
    parser.add_argument("--mode", type=str, default="default", help="Explanation mode.")
    parser.add_argument("--lang", type=str, default="english", help="Language (english/hindi).")
    args = parser.parse_args()

    result = query_rag(args.query_text, mode=args.mode, language=args.lang)
    print("\n=== Answer ===")
    print(result["answer"])
    print("\n=== Sources ===")
    for s in result["sources"]:
        print(" -", s)


if __name__ == "__main__":
    main()

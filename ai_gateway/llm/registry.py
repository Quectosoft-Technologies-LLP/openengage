"""
OpenEngage LLM Provider Registry
Supports: Ollama (default), OpenAI, Anthropic Claude, Google Gemini,
          xAI Grok, llama.cpp (local GGUF), Azure OpenAI.

Switch providers via environment:
  LLM_PROVIDER=ollama      (default — fully local, no API keys needed)
  LLM_PROVIDER=openai
  LLM_PROVIDER=claude
  LLM_PROVIDER=gemini
  LLM_PROVIDER=grok
  LLM_PROVIDER=llamacpp
  LLM_PROVIDER=azure_openai

All providers return a LangChain-compatible ChatModel — agents need zero changes.
"""
from __future__ import annotations
import os, logging
from typing import Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# ── Provider env vars (all optional except Ollama) ──────────
_PROVIDER        = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
_OLLAMA_URL      = os.getenv("OLLAMA_URL",       "http://ollama:11434")
_OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",      "qwen3:8b")
_OPENAI_KEY      = os.getenv("OPENAI_API_KEY",    "")
_OPENAI_MODEL    = os.getenv("OPENAI_MODEL",      "gpt-4o-mini")
_CLAUDE_KEY      = os.getenv("ANTHROPIC_API_KEY", "")
_CLAUDE_MODEL    = os.getenv("CLAUDE_MODEL",      "claude-3-5-haiku-20241022")
_GEMINI_KEY      = os.getenv("GOOGLE_API_KEY",    "")
_GEMINI_MODEL    = os.getenv("GEMINI_MODEL",      "gemini-2.0-flash")
_GROK_KEY        = os.getenv("GROK_API_KEY",      "")
_GROK_MODEL      = os.getenv("GROK_MODEL",        "grok-3-mini")
_GROK_BASE       = os.getenv("GROK_BASE_URL",     "https://api.x.ai/v1")
_LLAMACPP_URL    = os.getenv("LLAMACPP_URL",      "http://localhost:8080")
_LLAMACPP_MODEL  = os.getenv("LLAMACPP_MODEL",    "local-model")
_AZURE_KEY       = os.getenv("AZURE_OPENAI_KEY",  "")
_AZURE_ENDPOINT  = os.getenv("AZURE_OPENAI_ENDPOINT", "")
_AZURE_DEPLOY    = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
_AZURE_VERSION   = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# ── Temperature / generation config ─────────────────────────
_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS",    "2048"))


def get_llm(
    provider: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Any:
    """
    Return a LangChain ChatModel for the given provider.
    Falls back to Ollama if provider is unknown or import fails.

    Args:
        provider: Override LLM_PROVIDER env var (for per-agent overrides)
        temperature: Override LLM_TEMPERATURE
        max_tokens: Override LLM_MAX_TOKENS

    Returns:
        LangChain BaseChatModel instance (streaming-capable)

    Usage:
        llm = get_llm()                         # Uses .env LLM_PROVIDER
        llm = get_llm(provider="openai")        # Force OpenAI for this call
        llm = get_llm(temperature=0.7)          # Override temperature
    """
    p    = (provider or _PROVIDER).lower().strip()
    temp = temperature if temperature is not None else _TEMPERATURE
    mtok = max_tokens  if max_tokens  is not None else _MAX_TOKENS

    logger.info(f"Initializing LLM provider: {p}")

    try:
        if p == "ollama":
            return _build_ollama(temp, mtok)
        elif p == "openai":
            return _build_openai(temp, mtok)
        elif p in ("claude", "anthropic"):
            return _build_claude(temp, mtok)
        elif p in ("gemini", "google"):
            return _build_gemini(temp, mtok)
        elif p in ("grok", "xai"):
            return _build_grok(temp, mtok)
        elif p == "llamacpp":
            return _build_llamacpp(temp, mtok)
        elif p in ("azure_openai", "azure"):
            return _build_azure(temp, mtok)
        else:
            logger.warning(f"Unknown provider '{p}', falling back to Ollama")
            return _build_ollama(temp, mtok)
    except ImportError as e:
        logger.error(f"Provider '{p}' missing dependency: {e}. Falling back to Ollama.")
        return _build_ollama(temp, mtok)
    except Exception as e:
        logger.error(f"Provider '{p}' init failed: {e}. Falling back to Ollama.")
        return _build_ollama(temp, mtok)


# ── Provider Builders ─────────────────────────────────────────

def _build_ollama(temp: float, mtok: int):
    """Default — fully local, no API key, no data leaves your server."""
    from langchain_ollama import ChatOllama
    return ChatOllama(
        base_url=_OLLAMA_URL,
        model=_OLLAMA_MODEL,
        temperature=temp,
        num_predict=mtok,
    )


def _build_openai(temp: float, mtok: int):
    """OpenAI GPT-4o / GPT-4o-mini / o3-mini."""
    if not _OPENAI_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key=_OPENAI_KEY,
        model=_OPENAI_MODEL,
        temperature=temp,
        max_tokens=mtok,
        streaming=True,
    )


def _build_claude(temp: float, mtok: int):
    """Anthropic Claude 3.5 Haiku / Sonnet / Opus."""
    if not _CLAUDE_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        api_key=_CLAUDE_KEY,
        model=_CLAUDE_MODEL,
        temperature=temp,
        max_tokens=mtok,
    )


def _build_gemini(temp: float, mtok: int):
    """Google Gemini 2.0 Flash / Pro / Ultra."""
    if not _GEMINI_KEY:
        raise ValueError("GOOGLE_API_KEY not set")
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        google_api_key=_GEMINI_KEY,
        model=_GEMINI_MODEL,
        temperature=temp,
        max_output_tokens=mtok,
    )


def _build_grok(temp: float, mtok: int):
    """xAI Grok-3 / Grok-3-mini — OpenAI-compatible API."""
    if not _GROK_KEY:
        raise ValueError("GROK_API_KEY not set")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key=_GROK_KEY,
        base_url=_GROK_BASE,
        model=_GROK_MODEL,
        temperature=temp,
        max_tokens=mtok,
        streaming=True,
    )


def _build_llamacpp(temp: float, mtok: int):
    """
    llama.cpp server (local GGUF models via llama-server --port 8080).
    Run: llama-server -m ./models/qwen3-8b-q4.gguf --port 8080
    OpenAI-compatible API at http://localhost:8080/v1
    """
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key="not-needed",
        base_url=f"{_LLAMACPP_URL}/v1",
        model=_LLAMACPP_MODEL,
        temperature=temp,
        max_tokens=mtok,
        streaming=True,
    )


def _build_azure(temp: float, mtok: int):
    """Azure OpenAI — enterprise deployment with data residency."""
    if not _AZURE_KEY or not _AZURE_ENDPOINT:
        raise ValueError("AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT required")
    from langchain_openai import AzureChatOpenAI
    return AzureChatOpenAI(
        api_key=_AZURE_KEY,
        azure_endpoint=_AZURE_ENDPOINT,
        azure_deployment=_AZURE_DEPLOY,
        api_version=_AZURE_VERSION,
        temperature=temp,
        max_tokens=mtok,
        streaming=True,
    )


# ── Embedding model (for ChromaDB RAG) ───────────────────────
def get_embeddings(provider: str | None = None):
    """
    Return a LangChain Embeddings model.
    Default: Ollama nomic-embed-text (local).
    Falls back gracefully.
    """
    p = (provider or _PROVIDER).lower()
    try:
        if p in ("ollama", "llamacpp"):
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(base_url=_OLLAMA_URL, model="nomic-embed-text")
        elif p == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(api_key=_OPENAI_KEY, model="text-embedding-3-small")
        elif p in ("gemini", "google"):
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                google_api_key=_GEMINI_KEY, model="models/text-embedding-004"
            )
        else:
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(base_url=_OLLAMA_URL, model="nomic-embed-text")
    except Exception as e:
        logger.error(f"Embeddings init failed: {e}, falling back to Ollama")
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(base_url=_OLLAMA_URL, model="nomic-embed-text")


# ── Convenience: list available providers ────────────────────
PROVIDER_INFO = {
    "ollama":       {"name": "Ollama",          "local": True,  "needs_key": False, "models": ["qwen3:8b", "llama3.1:8b", "gemma3:12b", "mistral:7b"]},
    "openai":       {"name": "OpenAI",          "local": False, "needs_key": True,  "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"]},
    "claude":       {"name": "Anthropic Claude","local": False, "needs_key": True,  "models": ["claude-3-5-haiku-20241022", "claude-3-7-sonnet-20250219", "claude-opus-4-5"]},
    "gemini":       {"name": "Google Gemini",   "local": False, "needs_key": True,  "models": ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"]},
    "grok":         {"name": "xAI Grok",        "local": False, "needs_key": True,  "models": ["grok-3-mini", "grok-3", "grok-2"]},
    "llamacpp":     {"name": "llama.cpp",       "local": True,  "needs_key": False, "models": ["any GGUF model"]},
    "azure_openai": {"name": "Azure OpenAI",    "local": False, "needs_key": True,  "models": ["gpt-4o", "gpt-4o-mini"]},
}

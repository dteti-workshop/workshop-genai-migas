"""Factory embedding untuk Hari 2 (objek LangChain `Embeddings`)."""
from __future__ import annotations

from functools import lru_cache
from types import SimpleNamespace

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.embeddings import Embeddings

from common import config


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Kembalikan model embedding sesuai EMBED_PROVIDER di .env.

    - fastembed : model ONNX dijalankan lokal di CPU (default, tidak butuh API key).
                  Unduhan pertama ±220 MB ke folder EMBED_CACHE_DIR.
    - openai    : endpoint /v1/embeddings kompatibel OpenAI (Ollama, vLLM, TEI, dll).
    """
    if config.EMBED_PROVIDER == "fastembed":
        from langchain_community.embeddings import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=config.EMBED_MODEL, cache_dir=config.EMBED_CACHE_DIR)

    if config.EMBED_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=config.EMBED_MODEL,
            base_url=config.EMBED_BASE_URL,
            api_key=config.EMBED_API_KEY,
            check_embedding_ctx_length=False,  # wajib untuk server non-OpenAI (tanpa tiktoken)
        )

    raise ValueError(f"EMBED_PROVIDER tidak dikenal: {config.EMBED_PROVIDER}")


class _UsageCallback(BaseCallbackHandler):
    """Catat token panggilan LangChain ke penghitung yang sama dengan common.llm (usage_summary)."""

    def on_llm_end(self, response, **kwargs) -> None:
        from common import llm

        tu = (response.llm_output or {}).get("token_usage") or {}
        llm.USAGE.add(SimpleNamespace(prompt_tokens=tu.get("prompt_tokens", 0), completion_tokens=tu.get("completion_tokens", 0),
                                      model_extra={"cost": tu.get("cost", 0)}), 0)


def get_chat_model(temperature: float = 0.0, profile: str | None = None):
    """ChatOpenAI LangChain yang diarahkan ke profil online/local di .env."""
    from langchain_openai import ChatOpenAI

    p = config.get_profile(profile)
    kwargs = {}
    if p.is_openrouter:
        kwargs["default_headers"] = {"X-Title": "Workshop GenAI Migas"}
        kwargs["model_kwargs"] = {"user": config.PARTICIPANT_ID}
        from common.llm import extra_body  # penyedia model, mode reasoning, dan data biaya (sama dengan chat())

        kwargs["extra_body"] = extra_body(p.name)
    return ChatOpenAI(model=p.model, base_url=p.base_url, api_key=p.api_key or "none",
                      temperature=temperature, max_retries=5, callbacks=[_UsageCallback()], **kwargs)

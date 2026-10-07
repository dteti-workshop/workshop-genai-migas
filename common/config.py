"""Konfigurasi terpusat. Semua nilai dibaca dari file .env di root repo."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
CACHE = ROOT / ".cache"

load_dotenv(ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


@dataclass(frozen=True)
class LLMProfile:
    name: str
    base_url: str
    api_key: str
    model: str

    @property
    def is_openrouter(self) -> bool:
        return "openrouter.ai" in self.base_url


def get_profile(name: str | None = None) -> LLMProfile:
    """Ambil profil LLM ('online' / 'local'). Default: LLM_PROFILE di .env."""
    name = (name or _env("LLM_PROFILE", "online")).lower()
    prefix = name.upper()
    profile = LLMProfile(
        name=name,
        base_url=_env(f"{prefix}_BASE_URL"),
        api_key=_env(f"{prefix}_API_KEY"),
        model=_env(f"{prefix}_MODEL"),
    )
    if not profile.base_url or not profile.model:
        raise RuntimeError(
            f"Profil '{name}' belum lengkap. Isi {prefix}_BASE_URL dan {prefix}_MODEL di file .env"
        )
    return profile


PARTICIPANT_ID = _env("PARTICIPANT_ID", "anon")
MAX_CONCURRENCY = int(_env("LLM_MAX_CONCURRENCY", "4"))
USE_CACHE = _env("LLM_CACHE", "true").lower() in {"1", "true", "yes"}
REASONING_EFFORT = _env("LLM_REASONING_EFFORT", "none") or None
# Penyedia model pada OpenRouter (berurutan). Kosong berarti routing default OpenRouter.
PROVIDERS = [x.strip() for x in _env("ONLINE_PROVIDERS").split(",") if x.strip()]

EMBED_PROVIDER = _env("EMBED_PROVIDER", "fastembed").lower()
EMBED_MODEL = _env("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
EMBED_CACHE_DIR = str((ROOT / _env("EMBED_CACHE_DIR", "./models")).resolve())
EMBED_BASE_URL = _env("EMBED_BASE_URL")
EMBED_API_KEY = _env("EMBED_API_KEY", "local")

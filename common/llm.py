"""Helper LLM tipis di atas SDK `openai` (API kompatibel OpenAI).

Sengaja dibuat sederhana supaya peserta bisa membaca seluruh isinya.
Fitur:
- satu fungsi `chat()` untuk profil online (OpenRouter) maupun local
- retry + exponential backoff untuk 429 / timeout (API key dipakai bersama)
- cache SQLite untuk panggilan temperature=0 (eksperimen ulang tidak memakan kuota)
- pencatatan token & biaya (`usage_summary()`)
- `chat_detail()` untuk pengukuran: mengembalikan teks beserta jumlah token, biaya, latency, dan finish_reason
- `run_parallel()` untuk memproses banyak item dengan konkurensi terbatas
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import openai
from openai import OpenAI

from common import config

Messages = list[dict[str, str]]

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


@lru_cache(maxsize=4)
def get_client(profile: str | None = None) -> OpenAI:
    p = config.get_profile(profile)
    headers = {}
    if p.is_openrouter:
        headers = {"HTTP-Referer": "https://github.com/dteti-workshop/workshop-genai-migas", "X-Title": "Workshop GenAI Migas"}
    return OpenAI(base_url=p.base_url, api_key=p.api_key or "none", default_headers=headers, timeout=120, max_retries=0)


# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------


@dataclass
class Usage:
    calls: int = 0
    cache_hits: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, resp_usage: Any, latency: float) -> None:
        with self._lock:
            self.calls += 1
            self.latency_s += latency
            if resp_usage is None:
                return
            self.prompt_tokens += getattr(resp_usage, "prompt_tokens", 0) or 0
            self.completion_tokens += getattr(resp_usage, "completion_tokens", 0) or 0
            details = getattr(resp_usage, "completion_tokens_details", None)
            self.reasoning_tokens += getattr(details, "reasoning_tokens", 0) or 0
            extra = getattr(resp_usage, "model_extra", None) or {}
            self.cost_usd += float(extra.get("cost") or 0)


USAGE = Usage()


def usage_summary() -> str:
    u = USAGE
    avg = u.latency_s / u.calls if u.calls else 0
    return (
        f"Panggilan API: {u.calls} | cache hit: {u.cache_hits} | "
        f"token in/out: {u.prompt_tokens:,}/{u.completion_tokens:,} (reasoning {u.reasoning_tokens:,}) | "
        f"biaya: ${u.cost_usd:.4f} | rata-rata latensi: {avg:.1f}s"
    )


def reset_usage() -> None:
    global USAGE
    USAGE = Usage()


# ---------------------------------------------------------------------------
# Cache (hanya untuk temperature == 0, karena output deterministik-ish)
# ---------------------------------------------------------------------------

_CACHE_PATH = config.CACHE / "llm_cache.sqlite"
_cache_lock = threading.Lock()


def _cache_key(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _cache_get(key: str) -> str | None:
    if not _CACHE_PATH.exists():
        return None
    with _cache_lock, sqlite3.connect(_CACHE_PATH) as db:
        row = db.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def _cache_set(key: str, value: str) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _cache_lock, sqlite3.connect(_CACHE_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
        db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (key, value))


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

_RETRYABLE = (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError)


def _to_messages(prompt: str | Messages, system: str | None) -> Messages:
    msgs: Messages = [{"role": "system", "content": system}] if system else []
    if isinstance(prompt, str):
        msgs.append({"role": "user", "content": prompt})
    else:
        msgs.extend(prompt)
    return msgs


def chat(
    prompt: str | Messages,
    system: str | None = None,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    json_mode: bool = False,
    profile: str | None = None,
    model: str | None = None,
    use_cache: bool | None = None,
    retries: int = 5,
    reasoning: str | None = None,
) -> str:
    """Kirim prompt ke LLM dan kembalikan teks jawabannya.

    prompt     : string (pesan user) atau list messages [{"role":..., "content":...}]
    system     : system prompt opsional
    json_mode  : minta output JSON (response_format=json_object). Jika server tidak
                 mendukung, otomatis diulang tanpa parameter ini.
    profile    : 'online' / 'local' (default dari .env)
    reasoning  : mode berpikir model reasoning lewat OpenRouter: 'none' | 'low' | 'medium' | 'high'.
                 Default: LLM_REASONING_EFFORT di .env. Diabaikan untuk profil local.
    """
    p = config.get_profile(profile)
    messages = _to_messages(prompt, system)
    params: dict[str, Any] = {"model": model or p.model, "messages": messages, "temperature": temperature}
    if max_tokens:
        params["max_tokens"] = max_tokens
    if json_mode:
        params["response_format"] = {"type": "json_object"}

    effort = reasoning or config.REASONING_EFFORT
    cacheable = (config.USE_CACHE if use_cache is None else use_cache) and temperature == 0
    key = _cache_key({"base": p.base_url, "reasoning": effort, **params}) if cacheable else ""
    if cacheable and (hit := _cache_get(key)) is not None:
        USAGE.cache_hits += 1
        return hit

    resp, latency = _request(p, params, effort, retries)
    USAGE.add(resp.usage, latency)

    text = resp.choices[0].message.content or ""
    if cacheable:
        _cache_set(key, text)
    return text


def extra_body(profile: str | None = None, reasoning: str | None = None, exclude_reasoning: bool = True) -> dict[str, Any]:
    """Isi tambahan request khusus OpenRouter. Untuk profil lain dikembalikan dict kosong.

    usage     : biaya request ikut dikembalikan pada response
    provider  : membatasi penyedia model sesuai ONLINE_PROVIDERS agar jumlah token dan hasil konsisten
    reasoning : mode reasoning ('none' | 'low' | 'medium' | 'high'), default LLM_REASONING_EFFORT.
                Token reasoning selalu dihitung; teksnya hanya dikirim bila exclude_reasoning=False.
    """
    p = config.get_profile(profile)
    if not p.is_openrouter:
        return {}
    body: dict[str, Any] = {"usage": {"include": True}}
    if config.PROVIDERS:
        body["provider"] = {"order": config.PROVIDERS, "allow_fallbacks": False}
    effort = reasoning or config.REASONING_EFFORT
    if effort:
        body["reasoning"] = {"effort": effort, "exclude": exclude_reasoning}
    return body


def _request(p: config.LLMProfile, params: dict[str, Any], effort: str | None, retries: int,
             exclude_reasoning: bool = True) -> tuple[Any, float]:
    """Kirim satu request chat completion (dengan retry). Kembalikan (response, latency dalam detik)."""
    extra: dict[str, Any] = {}
    if p.is_openrouter:
        extra = {"user": config.PARTICIPANT_ID, "extra_body": extra_body(p.name, effort, exclude_reasoning)}

    client = get_client(p.name)
    for attempt in range(retries + 1):
        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(**params, **extra)
            break
        except openai.BadRequestError as e:
            if "response_format" in params:  # server/model tidak mendukung JSON mode
                params.pop("response_format")
                continue
            raise e
        except _RETRYABLE as e:
            if attempt == retries:
                raise
            wait = min(2**attempt + 0.5, 30)
            print(f"  [retry {attempt + 1}/{retries}] {type(e).__name__}, tunggu {wait:.0f}s ...")
            time.sleep(wait)
    return resp, time.perf_counter() - t0


@dataclass
class ChatResult:
    """Hasil satu pemanggilan LLM beserta data pengukurannya."""

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0  # sudah termasuk reasoning tokens
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    finish_reason: str = ""
    reasoning: str = ""  # teks reasoning, hanya terisi bila show_reasoning=True dan didukung penyedia
    provider: str = ""  # penyedia model yang melayani request (khusus OpenRouter)


def chat_detail(
    prompt: str | Messages,
    system: str | None = None,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    json_mode: bool = False,
    profile: str | None = None,
    model: str | None = None,
    reasoning: str | None = None,
    show_reasoning: bool = False,
    retries: int = 5,
) -> ChatResult:
    """Seperti chat(), tetapi mengembalikan ChatResult. Tidak memakai cache karena dipakai untuk pengukuran."""
    p = config.get_profile(profile)
    params: dict[str, Any] = {"model": model or p.model, "messages": _to_messages(prompt, system),
                              "temperature": temperature}
    if max_tokens:
        params["max_tokens"] = max_tokens
    if json_mode:
        params["response_format"] = {"type": "json_object"}
    resp, latency = _request(p, params, reasoning or config.REASONING_EFFORT, retries,
                             exclude_reasoning=not show_reasoning)
    USAGE.add(resp.usage, latency)
    u, msg = resp.usage, resp.choices[0].message
    details = getattr(u, "completion_tokens_details", None)
    return ChatResult(
        text=msg.content or "",
        prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(u, "completion_tokens", 0) or 0,
        reasoning_tokens=getattr(details, "reasoning_tokens", 0) or 0,
        cost_usd=float((getattr(u, "model_extra", None) or {}).get("cost") or 0),
        latency_s=latency,
        finish_reason=resp.choices[0].finish_reason or "",
        reasoning=getattr(msg, "reasoning", None) or (getattr(msg, "model_extra", None) or {}).get("reasoning") or "",
        provider=getattr(resp, "provider", None) or "",
    )


def chat_stream(prompt: str | Messages, system: str | None = None, *, temperature: float = 0.3,
                profile: str | None = None) -> Iterator[str]:
    """Versi streaming dari chat(): yield potongan teks satu per satu (dipakai di Streamlit)."""
    p = config.get_profile(profile)
    stream = get_client(p.name).chat.completions.create(
        model=p.model, messages=_to_messages(prompt, system), temperature=temperature, stream=True,
        **({"user": config.PARTICIPANT_ID, "extra_body": extra_body(p.name)} if p.is_openrouter else {}),
    )
    USAGE.add(None, 0)
    for chunk in stream:
        if chunk.choices and (delta := chunk.choices[0].delta.content):
            yield delta


# ---------------------------------------------------------------------------
# Utilitas
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_json(text: str) -> Any:
    """Parse JSON dari jawaban LLM secara toleran (menangani ```json ... ``` dan teks pengantar).

    Raise ValueError jika tidak ada JSON yang valid.
    """
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text]
    for c in candidates:
        c = c.strip()
        for opener, closer in (("{", "}"), ("[", "]")):
            start, end = c.find(opener), c.rfind(closer)
            if start != -1 and end > start:
                try:
                    return json.loads(c[start : end + 1])
                except json.JSONDecodeError:
                    pass
    raise ValueError(f"Tidak menemukan JSON valid pada jawaban: {text[:200]!r}")


def run_parallel(fn: Callable[[Any], Any], items: Iterable[Any], max_workers: int | None = None,
                 desc: str = "Memproses") -> list[Any]:
    """Jalankan fn(item) untuk setiap item secara paralel (urutan hasil = urutan input).

    Jika fn raise exception, hasil untuk item tsb berisi objek Exception (tidak menghentikan batch).
    """
    items = list(items)
    workers = min(max_workers or config.MAX_CONCURRENCY, config.MAX_CONCURRENCY)
    results: list[Any] = [None] * len(items)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, it): i for i, it in enumerate(items)}
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except Exception as e:  # noqa: BLE001
                results[i] = e
            done += 1
            if done % max(1, len(items) // 10) == 0 or done == len(items):
                print(f"  {desc}: {done}/{len(items)}")
    return results

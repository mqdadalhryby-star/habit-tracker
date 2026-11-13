"""طبقة النموذج اللغوي (LLM) — اختيارية وتعمل عبر واجهة OpenAI المتوافقة.

 الافتراضي: MiniMax (base: https://api.minimax.io/v1, model: MiniMax-M3.1-Flash).
 إن لم يوجد مفتاح API يعمل النظام بقواعده المحلية بلا إنترنت.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(
    os.environ.get("AI_BUILDER_CONFIG", Path.home() / ".config" / "ai-builder" / "config.json")
)

PROVIDERS = {
    "minimax": {
        "base_url": "https://api.minimax.io/v1",
        "model": "MiniMax-M3.1-Flash",
        "env_key": "MINIMAX_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
}


@dataclass
class LLMBackend:
    """واجهة بسيطة، أي مزوّد ينفّذها."""

    name: str = "none"

    def available(self) -> bool:
        return False

    def chat(self, system: str, user: str, max_tokens: int = 2000) -> str | None:
        return None


class OpenAICompatBackend(LLMBackend):
    """عميل chat/completions متوافق مع OpenAI (MiniMax، OpenAI، أو أي مزوّد آخر)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        name: str = "openai-compatible",
        timeout: int = 90,
    ) -> None:
        super().__init__(name=name)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, system: str, user: str, max_tokens: int = 2000) -> str | None:
        if not self.available():
            return None
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_completion_tokens": max_tokens,
        }
        response = self._post(payload)
        if response is None:
            # بعض المزوّدين لا تقبل كل الحقول — إعادة محاولة بحقول أقل.
            payload.pop("max_completion_tokens", None)
            payload["max_tokens"] = max_tokens
            response = self._post(payload)
        if response is None:
            return None
        try:
            message = response["choices"][0]["message"]
            content = message.get("content") or ""
            if isinstance(content, list):  # بعض المزوّدين يعيدون أجزاء
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            return content
        except (KeyError, IndexError, TypeError):
            return None

    def _post(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{self.base_url}/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"HTTP {e.code} من {url}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"تعذّر الاتصال بـ {url}: {e.reason}") from e


def load_config() -> dict[str, Any]:
    """قراءة ملف الإعداد المحفوظ (إن وُجد)."""
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_config(values: dict[str, Any]) -> Path:
    """حفظ الإعداد بصلاحيات مقيدة."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass
    return CONFIG_PATH


def build_backend(
    provider: str = "auto",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> LLMBackend:
    """بناء أفضل عميل متاح حسب الإعدادات ومتغيرات البيئة."""
    config = load_config()
    provider = provider or config.get("provider") or "auto"

    if provider == "none":
        return LLMBackend(name="none")

    if provider == "auto":
        if os.environ.get("MINIMAX_API_KEY") or config.get("minimax_api_key"):
            provider = "minimax"
        elif os.environ.get("OPENAI_API_KEY") or config.get("openai_api_key"):
            provider = "openai"
        else:
            return LLMBackend(name="none")

    defaults = PROVIDERS.get(provider, PROVIDERS["minimax"])
    key = api_key or config.get(f"{provider}_api_key") or os.environ.get(defaults["env_key"], "")
    url = base_url or config.get("base_url") or defaults["base_url"]
    name = model or config.get("model") or defaults["model"]
    if not key:
        return LLMBackend(name="none")
    return OpenAICompatBackend(base_url=url, api_key=key, model=name, name=provider)

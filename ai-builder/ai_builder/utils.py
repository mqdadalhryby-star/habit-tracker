"""أدوات مساعدة: أسماء صالحة، كتابة ملفات، استخراج JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def write_project_files(files: dict[str, str], out_dir: Path) -> list[Path]:
    """كتابة خريطة {مسار نسبي: محتوى} داخل out_dir وإرجاع قائمة الملفات المكتوبة."""
    written: list[Path] = []
    for rel_path, content in files.items():
        target = out_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return sorted(written)


def unique_dir(base: Path, name: str, force: bool = False) -> Path:
    """اختيار مجلد هدف فريد: name، ثم name-2، name-3 ..."""
    candidate = base / name
    if force or not candidate.exists():
        return candidate
    index = 2
    while (base / f"{name}-{index}").exists():
        index += 1
    return base / f"{name}-{index}"


def extract_json(text: str) -> dict[str, Any] | None:
    """استخراج أول كائن JSON من نص قد يحتوي أسواراً أو كوداً."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(cleaned[start : end + 1])
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def first_line(text: str, limit: int = 90) -> str:
    """أول سطر نظيف من نص، مقصوصاً عند حدّ معقول."""
    for raw in text.splitlines():
        line = raw.strip().lstrip("#-• ").strip()
        if line:
            return line[:limit]
    return text.strip()[:limit]

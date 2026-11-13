"""مولّدات المشاريع: كل مولّد ينتج ملفات مشروع كاملة قابلة للتشغيل."""

from __future__ import annotations

from .base import Generator
from .cli_tool import CLIToolGenerator
from .web_app import WebAppGenerator
from .api_service import APIServiceGenerator
from .script import ScriptGenerator
from .data_tool import DataToolGenerator

_REGISTRY = {
    CLIToolGenerator.kind: CLIToolGenerator,
    WebAppGenerator.kind: WebAppGenerator,
    APIServiceGenerator.kind: APIServiceGenerator,
    ScriptGenerator.kind: ScriptGenerator,
    DataToolGenerator.kind: DataToolGenerator,
}


def get_generator(kind: str) -> Generator:
    """إرجاع المولّد المناسب لنوع المشروع (مع بديل آمن)."""
    cls = _REGISTRY.get(kind, CLIToolGenerator)
    return cls()


__all__ = [
    "Generator",
    "CLIToolGenerator",
    "WebAppGenerator",
    "APIServiceGenerator",
    "ScriptGenerator",
    "DataToolGenerator",
    "get_generator",
]

"""تعريف المواصفة (Spec) التي يمثّل نية المستخدم بشكل منظّم."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

#: أنواع المشاريع التي يستطيع النموذج توليدها.
KINDS = ("cli_tool", "web_app", "api_service", "script", "data_tool")

KIND_LABELS = {
    "cli_tool": "أداة سطر أوامر (CLI)",
    "web_app": "تطبيق ويب",
    "api_service": "خدمة واجهة برمجية (API)",
    "script": "سكربت أتمتة",
    "data_tool": "أداة معالجة بيانات",
}


@dataclass
class Spec:
    """مواصفة المشروع المطلوب."""

    request: str
    kind: str = "cli_tool"
    name: str = "generated-tool"
    title: str = "Generated Tool"
    description: str = ""
    operations: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    entrypoint: str = ""
    language: str = "python"
    source: str = "rules"  # rules | llm | llm+rules

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            self.kind = "cli_tool"
        self.name = sanitize_identifier(self.name)
        self.title = (self.title or self.request).strip()
        self.description = (self.description or self.request).strip()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def kind_label(self) -> str:
        return KIND_LABELS.get(self.kind, self.kind)

    @property
    def primary_entity(self) -> str:
        return self.entities[0] if self.entities else "item"


def sanitize_identifier(name: str) -> str:
    """تحويل الاسم إلى معرّف صالح (underscore) للاستخدام في أسماء الملفات والوحدات."""
    import re

    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", (name or "").strip().lower())
    cleaned = re.sub(r"_{2,}", "_", cleaned).strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"gen_{cleaned}" if cleaned else "generated_tool"
    return cleaned

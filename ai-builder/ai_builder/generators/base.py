"""الواجهة الأساسية للمولّدات."""

from __future__ import annotations

from typing import Any

from ..spec import Spec


class Generator:
    """قاعدة المولّدات: يحوّل Spec إلى خريطة ملفات."""

    kind = "cli_tool"

    def generate(self, spec: Spec) -> dict[str, str]:
        """إرجاع {المسار النسبي: محتوى الملف}."""
        raise NotImplementedError

    # --- مساعدات مشتركة ---
    @staticmethod
    def readme(spec: Spec, run: list[str], extra: str = "") -> str:
        features = "\n".join(f"- {f}" for f in spec.features) or "- يعمل مباشرة بلا إعدادات"
        return f"""# {spec.title}

{spec.description}

## المزايا
{features}

## التشغيل
```bash
{chr(10).join(run)}
```

{extra}
## البنية
```
{spec.name}/
├── README.md
└── ... ملفات المشروع
```

> مولّد آلياً بواسطة `ai-builder` — عدّل ما يناسبك مباشرة.
"""

    @staticmethod
    def requirements(lines: list[str] | None = None) -> str:
        body = "\n".join(lines) if lines else "# لا تبعيات خارجية — مكتبة بايثون القياسية فقط"
        return body + "\n"

    @staticmethod
    def tests_init() -> str:
        return ""

"""محرك النية: يحوّل طلب المستخدم النصي إلى Spec بدون أي اعتماد خارجي.

 يعمل بمحرك قواعدي (سريع، بلا إنترنت) ويمكن تحسينه لاحقاً بنموذج LLM
 عبر llm.OpenAICompatBackend — انظر model.BuilderModel.
"""

from __future__ import annotations

import re
import sys

from .spec import Spec, sanitize_identifier

# ترتيب الفحص مهم: الأنواع الأخص قبل العامة.
_KIND_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "web_app",
        [
            "موقع", "صفحة", "تطبيق ويب", "ويب", "لوحة تحكم", "لوحة", "داشبورد",
            "dashboard", "واجهة", "متجر", "متجر إلكتروني", "website", "web app",
            "webapp", "landing", "frontend", "front-end", "ui", "تطبيق",
        ],
    ),
    (
        "api_service",
        [
            "api", "اواجهة برمجية", "واجهة برمجية", "rest", "restful", "خادم",
            "سيرفر", "server", "backend", "back-end", "microservice", "endpoint",
            "graphql", "نقطة نهاية",
        ],
    ),
    (
        "data_tool",
        [
            "csv", "excel", "xlsx", "spreadsheet", "جدول", "بيانات", "تحليل",
            "تنظيف بيانات", "تقرير", "pandas", "dataframe", "etl", "ديسكتوب",
            "erp", "قاعدة بيانات", "database", "dwh",
        ],
    ),
    (
        "script",
        [
            "سكربت", "script", "أتمتة", "automation", "مجدول", "cron", "batch",
            "نسخ احتياطي", "backup", "مهام يومية", "workflow", "خطوات", "jobs",
        ],
    ),
    (
        "cli_tool",
        [
            "cli", "سطر الاوامر", "سطر الأوامر", "command line", "command-line",
            "terminal", "أداة", "tool", "util", "utility", "محوّل", "converter",
            "مولد", "generator", "تنظيف", "clean",
        ],
    ),
]

# عمليات مدعومة تُترجم إلى دوال حقيقية داخل المشروع المولَّد.
_OP_PATTERNS: list[tuple[str, list[str]]] = [
    ("uppercase", ["حروف كبيرة", "كبيرة الحروف", "uppercase", "upper case", "to upper", "caps"]),
    ("lowercase", ["حروف صغيرة", "صغيرة الحروف", "lowercase", "to lower"]),
    ("reverse", ["عكس", "معكوس", "reverse", "backwards"]),
    ("sort", ["ترتيب", "رتب", "sort", "ascending", "تصاعدي"]),
    ("unique", ["تكرار", "مكرر", "فريد", "duplicate", "unique", "dedupe"]),
    ("trim", ["trim", "مسافات زائدة", "whitespace", "spaces"]),
    ("count", ["عدد", "احصاء", "إحصاء", "count", "stats", "statistics"]),
    ("json_format", ["json", "جيسون", "pretty print"]),
    ("convert_csv_json", ["csv إلى json", "csv to json", "csv2json"]),
    ("convert_json_csv", ["json إلى csv", "json to csv", "json2csv"]),
    ("rename", ["rename", "اعادة تسمية", "إعادة تسمية", "تسمية"]),
    ("copy", ["copy", "نسخ الملفات", "duplicate files"]),
    ("filter", ["فلتر", "تصفية", "filter"]),
    ("summarize", ["تلخيص", "summary", "summarize"]),
]

_ENTITY_HINTS = [
    "task", "note", "product", "customer", "order", "invoice", "employee",
    "article", "book", "contact", "habit", "expense", "student", "course",
    "مهمة", "ملاحظة", "منتج", "عميل", "طلب", "فاتورة", "موظف", "مقال", "كتاب",
    "ulfaq", "contact", "سجل", "حركة",
]

_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "to", "of", "with", "make", "create",
    "build", "tool", "that", "my", "please", "want", "need", "i", "me", "new",
    "and", "you", "it", "in", "on", "into", "from", "via", "using", "python",
}

_NAME_BY_KIND = {
    "cli_tool": "cli-tool",
    "web_app": "web-app",
    "api_service": "api-service",
    "script": "automation-script",
    "data_tool": "data-pipeline",
}

# أسماء يحجبها المشروع المولَّد: وحدات المكتبة القياسية وأسماء شائعة للمجلدات.
_RESERVED_NAMES = set(sys.stdlib_module_names) | {
    "app", "main", "index", "utils", "config", "data", "files", "static",
    "templates", "src", "docs", "build", "dist", "scripts", "lib", "bin",
    "logs", "tmp", "temp", "test", "tests", "readme", "license",
}

_KIND_PREFIX = {
    "cli_tool": "cli",
    "web_app": "web",
    "api_service": "api",
    "script": "auto",
    "data_tool": "data",
}


def _matches(text: str, patterns: list[str]) -> bool:
    """مطابقة النمط: حدود كلمة للأنماط اللاتينية، وتطابق نصي للأنماط العربية."""
    low = text.lower()
    for pattern in patterns:
        if pattern.isascii():
            if re.search(rf"(?<![a-z0-9]){re.escape(pattern.lower())}(?![a-z0-9])", low):
                return True
        elif pattern in text:
            return True
    return False


def detect_kind(text: str) -> str:
    """تحديد نوع المشروع من النص."""
    for kind, patterns in _KIND_PATTERNS:
        if _matches(text, patterns):
            return kind
    return "cli_tool"


def detect_operations(text: str, kind: str) -> list[str]:
    """استخراج العمليات المدعومة من النص."""
    found = [op for op, patterns in _OP_PATTERNS if _matches(text, patterns)]
    if not found:
        found = _DEFAULT_OPS.get(kind, ["count"])
    if kind == "data_tool" and not any(o.startswith("convert_") for o in found):
        found = found + ["convert_csv_json"]
    return found


_DEFAULT_OPS = {
    "cli_tool": ["uppercase", "count"],
    "web_app": ["add", "list", "done"],
    "api_service": ["create", "read", "update", "delete"],
    "script": ["scan", "backup"],
    "data_tool": ["clean", "summarize", "convert_csv_json"],
}


def detect_entities(text: str) -> list[str]:
    """تحديد الكيانات/النطاقات المحتملة."""
    hits: list[str] = []
    low = text.lower()
    for hint in _ENTITY_HINTS:
        if hint in low and hint not in hits:
            hits.append(hint)
    return hits[:3]


def detect_name(text: str, kind: str) -> str:
    """اشتقاق اسم مشروع صالح من النص (يتجنّب حجب وحدات المكتبة القياسية)."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", text)
    useful = [w.lower() for w in words if w.lower() not in _STOPWORDS]
    if useful:
        name = sanitize_identifier("-".join(useful[:3]))
    else:
        arabic = re.findall(r"[\u0600-\u06FF]{3,}", text)
        name = _NAME_BY_KIND.get(kind, "generated-tool") if arabic else _NAME_BY_KIND.get(kind, "generated-tool")

    if name in _RESERVED_NAMES:
        name = f"{_KIND_PREFIX.get(kind, 'gen')}_{name}"
    return sanitize_identifier(name)


def detect_title(text: str) -> str:
    """عنوان مختصر للعرض في README."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    for prefix in ("أنشئ لي ", "أنشئ ", "ابني لي ", "ابني ", "اعمل لي ", "سوّ ", "سوي ", "Make me ", "Build me ", "Create a "):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix) :].strip()
            break
    return cleaned[:70] or "Generated Project"


def analyze(request: str) -> Spec:
    """تحليل الطلب نصياً وإرجاع Spec كاملة."""
    text = (request or "").strip()
    kind = detect_kind(text)
    spec = Spec(
        request=text,
        kind=kind,
        name=detect_name(text, kind),
        title=detect_title(text),
        description=text,
        operations=detect_operations(text, kind),
        entities=detect_entities(text),
        source="rules",
    )
    spec.entrypoint = {
        "cli_tool": f"python3 {spec.name}.py --help",
        "web_app": "python3 -m http.server 8000   # ثم افتح http://localhost:8000",
        "api_service": "uvicorn app:app --reload --port 8000",
        "script": f"python3 {spec.name}.py --help",
        "data_tool": f"python3 {spec.name}.py --help",
    }[spec.kind]
    return spec

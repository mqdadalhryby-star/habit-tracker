"""النموذج: يخطّط ثم يولّد ثم يتحقق من المشروع."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .intent import analyze
from .llm import LLMBackend, build_backend
from .spec import Spec
from .utils import extract_json, unique_dir, write_project_files

SYSTEM_PROMPT = (
    "أنت مهندس برمجيات. مهمتك تحويل طلب المستخدم إلى مواصفة مشروع دقيقة. "
    "أجب بـ JSON صالح فقط دون أي نص إضافي أو أسوار كود."
)

USER_PROMPT_TEMPLATE = """طلب المستخدم:
\"\"\"{request}\"\"\"

أعد JSON فقط بالمخطط التالي:
{{
  "kind": "cli_tool" | "web_app" | "api_service" | "script" | "data_tool",
  "name": "slug_en_latin_snake_case",
  "title": "عنوان قصير",
  "description": "وصف وظيفي من سطرين",
  "operations": ["..."],  // عمليات من: uppercase, lowercase, reverse, sort, unique, trim, count, json_format, convert_csv_json, convert_json_csv, rename, copy, filter, summarize, clean
  "entities": ["..."],   // الكيانات المعرّفية (task, note, product, ...) حسب الطلب
  "features": ["..."]    // 3 إلى 6 ميزات ملموسة قابلة للتنفيذ
}}

قواعد:
- "kind" يطابق طبيعة الطلب.
- "name" بأحرف لاتينية صغيرة وشرطات، بلا مسافات.
- "operations" و"entities" و"features" بمحتوى مفيد فعلياً—not placeholders.
"""


@dataclass
class Verification:
    """نتيجة فحص واحد للمشروع المولَّد."""

    name: str
    ok: bool
    output: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "output": self.output}


@dataclass
class BuildResult:
    """نتيجة عملية البناء الكاملة."""

    spec: Spec
    project_dir: Path
    files: list[Path] = field(default_factory=list)
    verification: list[Verification] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(v.ok for v in self.verification) if self.verification else True

    def summary(self) -> str:
        lines = [
            f"النوع: {self.spec.kind_label}",
            f"الاسم: {self.spec.name}",
            f"المجلد: {self.project_dir}",
            f"الملفات: {len(self.files)}",
            f"التشغيل: {self.spec.entrypoint}",
        ]
        if self.verification:
            for v in self.verification:
                lines.append(f"[{'OK' if v.ok else 'FAIL'}] {v.name}")
        return "\n".join(lines)


class BuilderModel:
    """النموذج الذي يحوّل الطلب إلى مشروع قابل للتشغيل."""

    def __init__(
        self,
        backend: LLMBackend | None = None,
        verify: bool = True,
        timeout: int = 180,
    ) -> None:
        self.backend = backend if backend is not None else build_backend()
        self.verify = verify
        self.timeout = timeout

    # ---------- التخطيط ----------
    def plan(self, request: str) -> Spec:
        """تحليل الطلب محلياً ثم تحسينه بنموذج LLM إن توفّر."""
        spec = analyze(request)
        if not self.backend.available():
            return spec
        try:
            raw = self.backend.chat(
                SYSTEM_PROMPT,
                USER_PROMPT_TEMPLATE.format(request=request),
                max_tokens=1200,
            )
        except Exception as exc:  # فشل الاتصال لا يوقف البناء
            spec.source = f"rules (LLM unavailable: {exc})"
            return spec
        data = extract_json(raw or "")
        if not data:
            spec.source = "rules (LLM returned non-JSON)"
            return spec
        return self._merge(spec, data)

    def _merge(self, spec: Spec, data: dict[str, Any]) -> Spec:
        merged = spec.to_dict()
        for key in ("kind", "name", "title", "description"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()
        for key in ("operations", "entities", "features"):
            value = data.get(key)
            if isinstance(value, list) and value:
                items = [str(v).strip() for v in value if str(v).strip()]
                if items:
                    merged[key] = items
        merged["source"] = "llm+rules"
        return Spec(**merged)

    # ---------- البناء ----------
    def build(
        self,
        request: str,
        out_dir: str | Path = "./generated",
        kind: str | None = None,
        force: bool = False,
    ) -> BuildResult:
        """بناء المشروع كاملاً والتحقق من عمله."""
        from .generators import get_generator

        spec = self.plan(request)
        if kind:
            spec.kind = kind
        spec.entrypoint = self._entrypoint(spec)

        base = Path(out_dir).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        project_dir = unique_dir(base, spec.name, force=force)

        generator = get_generator(spec.kind)
        files = generator.generate(spec)
        written = write_project_files(files, project_dir)

        result = BuildResult(spec=spec, project_dir=project_dir, files=written)
        if self.verify:
            result.verification = self._verify(project_dir, spec)
        result.notes = self._notes(spec)
        return result

    def _entrypoint(self, spec: Spec) -> str:
        return {
            "cli_tool": f"python3 {spec.name}.py --help",
            "web_app": "python3 -m http.server 8000   # ثم افتح http://localhost:8000",
            "api_service": "uvicorn app:app --reload --port 8000",
            "script": f"python3 {spec.name}.py --help",
            "data_tool": f"python3 {spec.name}.py --help",
        }[spec.kind]

    # ---------- التحقق ----------
    def _verify(self, project_dir: Path, spec: Spec) -> list[Verification]:
        checks: list[Verification] = []

        tests_dir = project_dir / "tests"
        if tests_dir.is_dir():
            checks.append(
                self._run(
                    "اختبارات المشروع",
                    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"],
                    project_dir,
                )
            )

        if spec.kind == "cli_tool":
            checks.append(
                self._run(
                    "تشغيل الأداة (--help)",
                    [sys.executable, f"{spec.name}.py", "--help"],
                    project_dir,
                )
            )
        elif spec.kind == "script":
            checks.append(
                self._run(
                    "تشغيل السكربت (--help)",
                    [sys.executable, f"{spec.name}.py", "--help"],
                    project_dir,
                )
            )
        elif spec.kind == "data_tool":
            checks.append(
                self._run(
                    "تشغيل خط الأنابيب على البيانات التجريبية",
                    [sys.executable, f"{spec.name}.py", "--input", "data/sample.csv", "--output-dir", "out"],
                    project_dir,
                )
            )
        elif spec.kind == "api_service":
            logic_file = project_dir / "logic.py"
            if logic_file.exists():
                checks.append(
                    self._run(
                        "استيراد منطق الخدمة",
                        [sys.executable, "-c", "import logic; print('logic ok')"],
                        project_dir,
                    )
                )
        elif spec.kind == "web_app":
            index = project_dir / "index.html"
            ok = index.exists() and index.stat().st_size > 200
            checks.append(
                Verification(
                    "وجود صفحة index.html",
                    ok,
                    f"index.html: {index.stat().st_size} بايت" if index.exists() else "index.html مفقود",
                )
            )
        return checks

    def _run(self, name: str, command: list[str], cwd: Path) -> Verification:
        try:
            proc = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            output = (proc.stdout + proc.stderr).strip()
            if len(output) > 1200:
                output = output[:1200] + " ..."
            return Verification(name=name, ok=proc.returncode == 0, output=output)
        except subprocess.TimeoutExpired:
            return Verification(name=name, ok=False, output="انتهت المهلة")
        except OSError as exc:
            return Verification(name=name, ok=False, output=str(exc))

    def _notes(self, spec: Spec) -> list[str]:
        notes = [f"مصدر التخطيط: {spec.source}"]
        if not self.backend.available():
            notes.append(
                "النموذج اللغوي غير مفعّل — التخطيط تم بالمحرك القواعدي المحلي. "
                "لتفعيل LLM: ai-builder config --api-key <KEY> (أو اضبط MINIMAX_API_KEY)."
            )
        if spec.kind == "api_service":
            notes.append("يحتاج تشغيل الخدمة: pip install -r requirements.txt ثم uvicorn app:app")
        return notes

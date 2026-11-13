"""خادم منصة بناء الأدوات — واجهة ويب تستقبل أوامر نصية وتولّد مشاريع تعمل.

التشغيل:
    python3 platform/server.py            # ثم افتح http://localhost:8000
    PORT=9000 python3 platform/server.py

بلا أي تبعية خارجية: مكتبة بايثون القياسية فقط.
"""

from __future__ import annotations

import io
import json
import mimetypes
import os
import sys
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

PLATFORM_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PLATFORM_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from ai_builder.intent import analyze  # noqa: E402
from ai_builder.llm import build_backend, load_config, save_config  # noqa: E402
from ai_builder.model import BuilderModel  # noqa: E402
from ai_builder.spec import KIND_LABELS, KINDS  # noqa: E402

STATIC_DIR = PLATFORM_DIR / "static"
DATA_DIR = PLATFORM_DIR / "data"
GENERATED_DIR = Path(os.environ.get("PLATFORM_GENERATED_DIR", PLATFORM_DIR / "generated"))
HISTORY_PATH = DATA_DIR / "history.json"

MAX_BODY_BYTES = 1_000_000
BUILD_LOCK = threading.Lock()

TEXT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".py": "text/x-python; charset=utf-8",
    ".yml": "text/yaml; charset=utf-8",
    ".yaml": "text/yaml; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".zip": "application/zip",
}


# ---------------------------------------------------------------- أدوات مساعدة
def load_history() -> list[dict]:
    try:
        if HISTORY_PATH.exists():
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_history(entry: dict) -> None:
    history = load_history()
    history.insert(0, entry)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history[:50], ensure_ascii=False, indent=2), encoding="utf-8")


def list_projects() -> list[dict]:
    if not GENERATED_DIR.exists():
        return []
    projects = []
    for folder in sorted(GENERATED_DIR.iterdir()):
        if not folder.is_dir():
            continue
        files = [p for p in folder.rglob("*") if p.is_file()]
        size = sum(p.stat().st_size for p in files)
        projects.append(
            {
                "name": folder.name,
                "files": len(files),
                "size": size,
                "modified": folder.stat().st_mtime,
                "has_web": (folder / "index.html").exists(),
            }
        )
    projects.sort(key=lambda item: item["modified"], reverse=True)
    return projects


def safe_join(base: Path, relative: str) -> Path | None:
    """منع الخروج من المجلد المسموح (path traversal)."""
    target = (base / unquote(relative).lstrip("/")).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


def zip_project(folder: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(folder))
    return buffer.getvalue()


# ---------------------------------------------------------------------- الخادم
class PlatformHandler(BaseHTTPRequestHandler):
    server_version = "AiBuilderPlatform/1.0"

    def log_message(self, fmt, *args):  # سجل مختصر
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    # ---------- أدوات الإرسال ----------
    def _send_bytes(self, payload: bytes, content_type: str, status: int = 200, extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _send_json(self, obj, status: int = 200):
        payload = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self._send_bytes(payload, "application/json; charset=utf-8", status)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError("حجم الطلب كبير جداً")
        raw = self.rfile.read(length).decode("utf-8", "replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON غير صالح: {exc}") from exc
        return data if isinstance(data, dict) else {}

    # ---------- GET ----------
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path in ("/", "/index.html"):
                return self._serve_static("index.html")
            if path.startswith("/static/"):
                return self._serve_static(path[len("/static/"):])
            if path == "/api/status":
                return self._api_status()
            if path == "/api/projects":
                return self._send_json({"projects": list_projects(), "history": load_history()})
            if path == "/api/files":
                return self._api_files(query)
            if path == "/api/download":
                return self._api_download(query)
            if path.startswith("/preview/"):
                return self._serve_preview(path[len("/preview/"):])
            self._send_json({"error": "المسار غير موجود"}, 404)
        except Exception as exc:  # pylint: disable=broad-except
            self._send_json({"error": str(exc)}, 500)

    # ---------- POST ----------
    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self._read_json()
            if path == "/api/build":
                return self._api_build(payload)
            if path == "/api/config":
                return self._api_config(payload)
            self._send_json({"error": "المسار غير موجود"}, 404)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)
        except Exception as exc:  # pylint: disable=broad-except
            self._send_json({"error": str(exc)}, 500)

    # ---------- تنفيذ ----------
    def _serve_static(self, relative: str):
        target = safe_join(STATIC_DIR, relative)
        if target is None or not target.is_file():
            return self._send_json({"error": "الملف غير موجود"}, 404)
        ctype = TEXT_TYPES.get(target.suffix.lower(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self._send_bytes(target.read_bytes(), ctype)

    def _serve_preview(self, relative: str):
        parts = relative.split("/", 1)
        project = parts[0]
        rest = parts[1] if len(parts) > 1 else "index.html"
        base = safe_join(GENERATED_DIR, project)
        if base is None or not base.is_dir():
            return self._send_json({"error": "المشروع غير موجود"}, 404)
        target = safe_join(base, rest)
        if target is None or not target.is_file():
            return self._send_json({"error": "الملف غير موجود"}, 404)
        ctype = TEXT_TYPES.get(target.suffix.lower(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self._send_bytes(target.read_bytes(), ctype)

    def _api_status(self):
        config = load_config()
        has_key = bool(config.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY"))
        backend = build_backend(provider=config.get("provider", "auto"))
        return self._send_json(
            {
                "llm": {
                    "enabled": backend.available(),
                    "provider": getattr(backend, "name", "none"),
                    "model": getattr(backend, "model", "-"),
                    "api_key_present": has_key,
                },
                "kinds": {kind: KIND_LABELS[kind] for kind in KINDS},
                "projects": len(list_projects()),
                "generated_dir": str(GENERATED_DIR),
            }
        )

    def _api_config(self, payload: dict):
        api_key = (payload.get("api_key") or "").strip()
        config = load_config()
        if api_key:
            config["minimax_api_key"] = api_key
            config["provider"] = "minimax"
        if payload.get("provider"):
            config["provider"] = payload["provider"]
        if payload.get("model"):
            config["model"] = payload["model"]
        path = save_config(config)
        backend = build_backend(provider=config.get("provider", "auto"))
        return self._send_json(
            {"saved": True, "path": str(path), "llm_enabled": backend.available()}
        )

    def _api_build(self, payload: dict):
        request = (payload.get("request") or "").strip()
        if not request:
            return self._send_json({"error": "الطلب فارغ — اكتب ما تريد بناءه."}, 400)
        if len(request) > 2000:
            return self._send_json({"error": "الطلب طويل جداً (الحد 2000 حرف)."}, 400)
        kind = payload.get("kind") or None
        if kind and kind not in KINDS:
            kind = None
        verify = bool(payload.get("verify", True))

        backend = build_backend(
            provider=payload.get("provider"),
            model=payload.get("model"),
            api_key=(payload.get("api_key") or "").strip() or None,
        )
        model = BuilderModel(backend=backend, verify=verify)

        with BUILD_LOCK:
            started = time.time()
            result = model.build(request, out_dir=GENERATED_DIR, kind=kind)
            elapsed = round(time.time() - started, 2)

        files = []
        for file_path in result.files:
            files.append(
                {
                    "path": str(file_path.relative_to(result.project_dir)),
                    "size": file_path.stat().st_size,
                }
            )

        entry = {
            "request": request,
            "project": result.project_dir.name,
            "kind": result.spec.kind,
            "title": result.spec.title,
            "timestamp": time.time(),
            "ok": result.ok,
        }
        save_history(entry)

        return self._send_json(
            {
                "project": result.project_dir.name,
                "dir": str(result.project_dir),
                "spec": result.spec.to_dict(),
                "kind_label": result.spec.kind_label,
                "files": files,
                "verification": [v.as_dict() for v in result.verification],
                "notes": result.notes,
                "entrypoint": result.spec.entrypoint,
                "ok": result.ok,
                "elapsed": elapsed,
                "download": f"/api/download?name={result.project_dir.name}",
                "preview": f"/preview/{result.project_dir.name}/index.html"
                if (result.project_dir / "index.html").exists()
                else None,
            }
        )

    def _api_files(self, query: dict):
        project = (query.get("name") or [""])[0]
        relative = (query.get("path") or [""])[0]
        base = safe_join(GENERATED_DIR, project)
        if base is None or not base.is_dir():
            return self._send_json({"error": "المشروع غير موجود"}, 404)
        if not relative:
            tree = []
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    tree.append(
                        {
                            "path": str(path.relative_to(base)),
                            "size": path.stat().st_size,
                        }
                    )
            return self._send_json({"files": tree})
        target = safe_join(base, relative)
        if target is None or not target.is_file():
            return self._send_json({"error": "الملف غير موجود"}, 404)
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return self._send_json({"error": "ملف ثنائي — لا يمكن عرضه كنص"}, 415)
        return self._send_json({"path": relative, "content": content})

    def _api_download(self, query: dict):
        project = (query.get("name") or [""])[0]
        base = safe_join(GENERATED_DIR, project)
        if base is None or not base.is_dir():
            return self._send_json({"error": "المشروع غير موجود"}, 404)
        payload = zip_project(base)
        filename = f"{project}.zip"
        self._send_bytes(
            payload,
            "application/zip",
            extra={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


def serve(port: int = 8000, host: str = "0.0.0.0") -> ThreadingHTTPServer:
    """بدء الخادم."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((host, port), PlatformHandler)
    print("=" * 62)
    print("  منصة بناء الأدوات — AiBuilder Platform")
    print(f"  افتح: http://localhost:{port}")
    print(f"  المشاريع المولَّدة: {GENERATED_DIR}")
    print("=" * 62)
    return httpd


def main() -> int:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    httpd = serve(port, host)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nتم إيقاف الخادم.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

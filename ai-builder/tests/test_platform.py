"""اختبارات منصة بناء الأدوات — تشغيل الخادم فعلياً والتحقق من كل نقاط API."""

import io
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys_path = str(ROOT)
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

# مجلد مؤقت للمشاريع المولَّدة حتى لا نلوّث مجلد العمل
TMP = tempfile.mkdtemp(prefix="platform-tests-")
os.environ["PLATFORM_GENERATED_DIR"] = TMP

from studio import server  # noqa: E402

BASE = ""


class TestPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = server.serve(port=0, host="127.0.0.1")
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(TMP, ignore_errors=True)

    def _get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=120) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type", "")

    def _post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    # ---------- الواجهة ----------
    def test_home_page_serves_ui(self):
        status, body, ctype = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("منصة بناء الأدوات", body.decode("utf-8"))

    def test_static_assets(self):
        for asset in ("/static/styles.css", "/static/app.js"):
            status, body, _ = self._get(asset)
            self.assertEqual(status, 200, asset)
            self.assertGreater(len(body), 200)

    def test_status_endpoint(self):
        status, body, _ = self._get("/api/status")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("llm", data)
        self.assertIn("cli_tool", data["kinds"])

    # ---------- البناء ----------
    def test_build_cli_tool(self):
        status, data = self._post("/api/build", {"request": "أنشئ لي أداة سطر أوامر تحوّل الحروف إلى حروف كبيرة", "verify": True})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"], data)
        self.assertEqual(data["spec"]["kind"], "cli_tool")
        self.assertGreater(len(data["files"]), 3)
        self.assertTrue(data["verification"])
        self.assertTrue(all(v["ok"] for v in data["verification"]))

        project_dir = Path(data["dir"])
        self.assertTrue(project_dir.is_dir())
        self.assertTrue((project_dir / "README.md").exists())

    def test_build_web_app_and_preview(self):
        status, data = self._post("/api/build", {"request": "أنشئ لي تطبيق ويب لمتابعة العادات", "verify": True})
        self.assertEqual(status, 200)
        self.assertEqual(data["spec"]["kind"], "web_app")
        self.assertIsNotNone(data["preview"])

        pstatus, body, ctype = self._get(data["preview"])
        self.assertEqual(pstatus, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("<html", body.decode("utf-8"))

    def test_build_rejects_empty_request(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("/api/build", {"request": "   "})
        self.assertEqual(ctx.exception.code, 400)

    # ---------- الملفات والتنزيل ----------
    def test_list_files_and_read_content(self):
        _, data = self._post("/api/build", {"request": "أنشئ لي أداة بيانات تنظف ملف CSV وتنتج تقريراً", "verify": False})
        name = data["project"]

        status, body, _ = self._get(f"/api/files?name={name}")
        self.assertEqual(status, 200)
        tree = json.loads(body.decode("utf-8"))["files"]
        self.assertTrue(tree)

        target = next(f["path"] for f in tree if f["path"].endswith(".py"))
        status, body, _ = self._get(f"/api/files?name={name}&path={target}")
        self.assertEqual(status, 200)
        self.assertIn("def main", json.loads(body.decode("utf-8"))["content"])

    def test_download_zip_is_valid(self):
        _, data = self._post("/api/build", {"request": "أنشئ لي سكربت أتمتة للنسخ الاحتياطي", "verify": False})
        name = data["project"]
        status, body, _ = self._get(f"/api/download?name={name}")
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            names = archive.namelist()
        self.assertTrue(any(n.endswith("README.md") for n in names))

    def test_projects_endpoint_lists_results(self):
        status, body, _ = self._get("/api/projects")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertGreaterEqual(len(data["projects"]), 3)
        self.assertTrue(data["history"])

    # ---------- الأمان ----------
    def test_path_traversal_is_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/files?name=../../etc&path=passwd")
        self.assertIn(ctx.exception.code, (400, 404))

    def test_preview_rejects_escape(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/preview/..%2F..%2Fetc/passwd")
        self.assertIn(ctx.exception.code, (400, 404))


if __name__ == "__main__":
    unittest.main()

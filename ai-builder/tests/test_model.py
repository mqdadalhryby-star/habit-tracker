"""اختبارات end-to-end: توليد كل نوع مشروع والتأكد أن اختباراته تعمل."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_builder.model import BuilderModel

REQUESTS = {
    "cli_tool": "أنشئ لي أداة سطر أوامر تحوّل الحروف إلى حروف كبيرة وتزيل التكرار",
    "web_app": "أنشئ لي تطبيق ويب لمتابعة المهام اليومية",
    "api_service": "أنشئ لي REST API لإدارة الطلبات",
    "script": "أنشئ لي سكربت أتمتة للنسخ الاحتياطي من مجلد",
    "data_tool": "أنشئ لي أداة بيانات تنظف ملف CSV وتنتج تقريراً",
}


class TestGeneratedProjects(unittest.TestCase):
    def _build(self, kind: str, out_dir: Path) -> Path:
        model = BuilderModel(verify=False)
        result = model.build(REQUESTS[kind], out_dir=out_dir, kind=kind)
        return result.project_dir

    def test_each_kind_generates_runnable_project(self):
        for kind, request in REQUESTS.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                project = self._build(kind, Path(tmp))
                self.assertTrue((project / "README.md").exists())
                self.assertTrue((project / "tests").is_dir())

                proc = subprocess.run(
                    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"],
                    cwd=str(project),
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    f"اختبارات المشروع المولَّد ({kind}) فشلت:\n{proc.stdout}\n{proc.stderr}",
                )

    def test_cli_project_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._build("cli_tool", Path(tmp))
            main_file = next(project.glob("*.py"))
            proc = subprocess.run(
                [sys.executable, main_file.name, "--help"],
                cwd=str(project),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertIn("--op", proc.stdout)

    def test_data_project_produces_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._build("data_tool", Path(tmp))
            main_file = next(project.glob("*.py"))
            proc = subprocess.run(
                [
                    sys.executable,
                    main_file.name,
                    "--input",
                    "data/sample.csv",
                    "--output-dir",
                    "out",
                ],
                cwd=str(project),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((project / "out" / "cleaned.csv").exists())
            self.assertTrue((project / "out" / "report.md").exists())

    def test_script_project_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._build("script", Path(tmp))
            main_file = next(project.glob("*.py"))
            proc = subprocess.run(
                [sys.executable, main_file.name, "scan", "."],
                cwd=str(project),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("total_files", proc.stdout)

    def test_build_is_repeatable_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = self._build("cli_tool", Path(tmp))
            second = self._build("cli_tool", Path(tmp))
            self.assertNotEqual(first, second)
            self.assertTrue(first.exists() and second.exists())


if __name__ == "__main__":
    unittest.main()

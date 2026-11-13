"""اختبارات نواة ai-builder."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_builder.intent import analyze, detect_kind, detect_operations
from ai_builder.spec import Spec, sanitize_identifier
from ai_builder.utils import extract_json


class TestIntent(unittest.TestCase):
    def test_detect_web_app(self):
        self.assertEqual(detect_kind("أنشئ لي موقع تجارة إلكترونية"), "web_app")

    def test_detect_api(self):
        self.assertEqual(detect_kind("build a REST api for orders"), "api_service")

    def test_detect_data_tool(self):
        self.assertEqual(detect_kind("أداة تحليل بيانات CSV مع تقرير"), "data_tool")

    def test_detect_script(self):
        self.assertEqual(detect_kind("سكربت أتمتة للنسخ الاحتياطي"), "script")

    def test_default_is_cli(self):
        self.assertEqual(detect_kind("شيء ما"), "cli_tool")

    def test_operations_detected(self):
        ops = detect_operations("أداة تحويل الحروف إلى حروف كبيرة وإزالة التكرار", "cli_tool")
        self.assertIn("uppercase", ops)
        self.assertIn("unique", ops)

    def test_spec_has_entrypoint(self):
        spec = analyze("أنشئ أداة سطر أوامر لتحويل الملفات")
        self.assertTrue(spec.entrypoint)
        self.assertEqual(spec.source, "rules")


class TestSpec(unittest.TestCase):
    def test_sanitize_identifier(self):
        self.assertEqual(sanitize_identifier("My Tool!"), "my_tool")
        self.assertTrue(sanitize_identifier("123abc").startswith("gen_"))

    def test_unknown_kind_falls_back(self):
        self.assertEqual(Spec(request="x", kind="unknown").kind, "cli_tool")


class TestUtils(unittest.TestCase):
    def test_extract_json_from_fenced_text(self):
        raw = '```json\n{"kind": "cli_tool", "name": "x"}\n```'
        self.assertEqual(extract_json(raw)["name"], "x")

    def test_extract_json_from_mixed_text(self):
        raw = 'إليك المواصفة: {"kind": "web_app"} — انتهى.'
        self.assertEqual(extract_json(raw)["kind"], "web_app")

    def test_extract_json_invalid(self):
        self.assertIsNone(extract_json("لا يوجد JSON هنا"))


if __name__ == "__main__":
    unittest.main()

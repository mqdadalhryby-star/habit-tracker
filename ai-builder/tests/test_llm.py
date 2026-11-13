"""اختبارات طبقة LLM — باستخدام خادم HTTP محلي وهمي (بلا إنترنت)."""

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_builder.llm import OpenAICompatBackend
from ai_builder.model import BuilderModel
from ai_builder.spec import Spec

CANNED = {
    "kind": "web_app",
    "name": "habit_tracker",
    "title": "متتبع العادات",
    "description": "تطبيق ويب لمتابعة العادات اليومية",
    "operations": ["add", "list", "done"],
    "entities": ["habit"],
    "features": ["تتبع يومي", "إحصائيات", "حفظ محلي"],
}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = json.dumps(
            {
                "id": "chatcmpl-mock",
                "model": "mock",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "```json\n" + json.dumps(CANNED) + "\n```"}}
                ],
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # إسكات السجل
        return


class TestLLMLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_backend_returns_content(self):
        backend = OpenAICompatBackend(self.base_url, "test-key", "mock")
        self.assertTrue(backend.available())
        out = backend.chat("system", "user")
        self.assertIn("habit_tracker", out)

    def test_plan_merges_llm_spec(self):
        backend = OpenAICompatBackend(self.base_url, "test-key", "mock")
        model = BuilderModel(backend=backend, verify=False)
        spec = model.plan("أنشئ لي تطبيق ويب لمتابعة العادات")
        self.assertEqual(spec.source, "llm+rules")
        self.assertEqual(spec.kind, "web_app")
        self.assertEqual(spec.name, "habit_tracker")
        self.assertIn("تتبع يومي", spec.features)

    def test_local_rules_still_used_without_backend(self):
        class NoBackend(OpenAICompatBackend):
            def available(self):
                return False

        model = BuilderModel(backend=NoBackend("http://x/v1", "", "mock"), verify=False)
        spec = model.plan("أنشئ لي أداة سطر أوامر")
        self.assertEqual(spec.source, "rules")
        self.assertEqual(spec.kind, "cli_tool")

    def test_llm_failure_falls_back_to_rules(self):
        class BrokenBackend(OpenAICompatBackend):
            def chat(self, system, user, max_tokens=2000):
                raise RuntimeError("network down")

        model = BuilderModel(backend=BrokenBackend("http://x/v1", "k", "m"), verify=False)
        spec = model.plan("أنشئ لي REST API للطلبات")
        self.assertTrue(spec.source.startswith("rules"))
        self.assertEqual(spec.kind, "api_service")


if __name__ == "__main__":
    unittest.main()

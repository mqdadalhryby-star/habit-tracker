"""مولّد خدمة API: منطق نقي + واجهة FastAPI."""

from __future__ import annotations

from string import Template

from ..spec import Spec
from .base import Generator

LOGIC_TEMPLATE = Template(
    '''"""منطق الخدمة — وحدة نقية بلا اعتماد على FastAPI (قابلة للاختبار وحدها)."""

from __future__ import annotations

from typing import Any

MAX_TITLE = 200


class ValidationError(ValueError):
    """خطأ في بيانات الإدخال."""


class Store:
    """مخزن عناصر في الذاكرة مع ترقيم تلقائي."""

    def __init__(self) -> None:
        self._items: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title", "")).strip()
        if not title:
            raise ValidationError("الحقل title مطلوب")
        if len(title) > MAX_TITLE:
            raise ValidationError(f"title أطول من {MAX_TITLE} حرفاً")
        item = {
            "id": self._next_id,
            "title": title,
            "notes": str(payload.get("notes", "")).strip(),
            "done": bool(payload.get("done", False)),
        }
        self._next_id += 1
        self._items[item["id"]] = item
        return dict(item)

    def list(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items.values()]

    def get(self, item_id: int) -> dict[str, Any] | None:
        item = self._items.get(item_id)
        return dict(item) if item else None

    def update(self, item_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        item = self._items.get(item_id)
        if item is None:
            return None
        if "title" in payload:
            title = str(payload.get("title", "")).strip()
            if not title:
                raise ValidationError("الحقل title لا يمكن أن يكون فارغاً")
            item["title"] = title
        if "notes" in payload:
            item["notes"] = str(payload.get("notes", "")).strip()
        if "done" in payload:
            item["done"] = bool(payload.get("done"))
        return dict(item)

    def delete(self, item_id: int) -> bool:
        return self._items.pop(item_id, None) is not None

    def clear(self) -> int:
        count = len(self._items)
        self._items.clear()
        return count
'''
)

APP_TEMPLATE = Template(
    '''"""خدمة $title — FastAPI

التشغيل:
    pip install -r requirements.txt
    uvicorn app:app --reload --port 8000
    ثم افتح http://localhost:8000/docs
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from logic import Store, ValidationError

app = FastAPI(title="$title", version="1.0.0", description="$description")
store = Store()


class ItemIn(BaseModel):
    title: str = Field(..., description="عنوان العنصر", min_length=1, max_length=200)
    notes: str = Field("", description="ملاحظات اختيارية")
    done: bool = Field(False, description="هل العنصر منتهٍ؟")


class ItemUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    done: bool | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "$name"}


@app.get("/items")
def list_items() -> dict[str, Any]:
    items = store.list()
    return {"count": len(items), "items": items}


@app.post("/items", status_code=201)
def create_item(payload: ItemIn) -> dict[str, Any]:
    try:
        return store.create(payload.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/items/{item_id}")
def get_item(item_id: int) -> dict[str, Any]:
    item = store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="العنصر غير موجود")
    return item


@app.patch("/items/{item_id}")
def update_item(item_id: int, payload: ItemUpdate) -> dict[str, Any]:
    try:
        item = store.update(item_id, payload.model_dump(exclude_none=True))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="العنصر غير موجود")
    return item


@app.delete("/items/{item_id}")
def delete_item(item_id: int) -> dict[str, Any]:
    if not store.delete(item_id):
        raise HTTPException(status_code=404, detail="العنصر غير موجود")
    return {"deleted": item_id}
'''
)

TEST_TEMPLATE = Template(
    '''"""اختبارات منطق الخدمة $title"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logic import Store, ValidationError


class TestStore(unittest.TestCase):
    def setUp(self):
        self.store = Store()

    def test_create_and_list(self):
        item = self.store.create({"title": "عنصر أول"})
        self.assertEqual(item["id"], 1)
        self.assertEqual(len(self.store.list()), 1)

    def test_create_requires_title(self):
        with self.assertRaises(ValidationError):
            self.store.create({"title": "   "})

    def test_update_and_delete(self):
        item = self.store.create({"title": "عنصر"})
        updated = self.store.update(item["id"], {"title": "عنصر معدّل", "done": True})
        self.assertEqual(updated["title"], "عنصر معدّل")
        self.assertTrue(updated["done"])
        self.assertTrue(self.store.delete(item["id"]))
        self.assertIsNone(self.store.get(item["id"]))

    def test_missing_item(self):
        self.assertIsNone(self.store.get(99))
        self.assertFalse(self.store.delete(99))


if __name__ == "__main__":
    unittest.main()
'''
)


class APIServiceGenerator(Generator):
    kind = "api_service"

    def generate(self, spec: Spec) -> dict[str, str]:
        readme = self.readme(
            spec,
            run=[
                "pip install -r requirements.txt",
                "uvicorn app:app --reload --port 8000",
                "# التوثيق التفاعلي: http://localhost:8000/docs",
                "python3 -m unittest discover -s tests -t . -v",
            ],
            extra="## النقاط (Endpoints)\n"
            "| الطريقة | المسار | الوصف |\n|---|---|---|\n"
            "| GET | `/health` | فحص الجاهزية |\n"
            "| GET | `/items` | قائمة العناصر |\n"
            "| POST | `/items` | إنشاء عنصر |\n"
            "| GET | `/items/{id}` | عنصر واحد |\n"
            "| PATCH | `/items/{id}` | تحديث جزئي |\n"
            "| DELETE | `/items/{id}` | حذف |\n\n"
            "> التخزين في الذاكرة (in-memory) — استبدله بقاعدة بيانات للاستخدام الحقيقي.\n\n",
        )

        return {
            "app.py": APP_TEMPLATE.substitute(
                title=spec.title, description=spec.description, name=spec.name
            ),
            "logic.py": LOGIC_TEMPLATE.substitute(),
            "requirements.txt": self.requirements(
                ["fastapi>=0.110", "uvicorn[standard]>=0.27", "pydantic>=2.6"]
            ),
            "README.md": readme,
            "tests/__init__.py": "",
            "tests/test_logic.py": TEST_TEMPLATE.substitute(title=spec.title),
        }

"""مولّد تطبيق ويب: صفحة واحدة تعمل بلا إعدادات مع تخزين محلي."""

from __future__ import annotations

from string import Template

from ..spec import Spec
from .base import Generator

HTML_TEMPLATE = Template(
    '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>$title</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="topbar">
    <h1>$title</h1>
    <p class="subtitle">$description</p>
  </header>

  <main class="container">
    <form id="entry-form" class="entry-form" autocomplete="off">
      <input id="entry-input" type="text" placeholder="$placeholder" required>
      <button type="submit" id="add-button">إضافة</button>
    </form>

    <section class="toolbar">
      <div class="filters" role="group" aria-label="تصفية">
        <button class="filter active" data-filter="all">الكل</button>
        <button class="filter" data-filter="active">غير منتهٍ</button>
        <button class="filter" data-filter="done">منتهٍ</button>
      </div>
      <span id="counter" class="counter">0 عنصر</span>
    </section>

    <ul id="entry-list" class="entry-list" aria-live="polite"></ul>
    <p id="empty-state" class="empty">لا توجد عناصر بعد — أضف أول عنصر من الأعلى.</p>
  </main>

  <template id="entry-template">
    <li class="entry">
      <label class="entry-main">
        <input type="checkbox" class="toggle">
        <span class="entry-text"></span>
      </label>
      <button class="delete" type="button" aria-label="حذف">✕</button>
    </li>
  </template>

  <script src="app.js"></script>
</body>
</html>
'''
)

CSS_TEMPLATE = Template(
    ''':root {
  --bg: #0f1420;
  --panel: #171e2e;
  --accent: #4f8cff;
  --text: #e9eef7;
  --muted: #8b97ad;
  --danger: #ff6b6b;
  --radius: 12px;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: "Segoe UI", Tahoma, system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}

.topbar {
  padding: 28px 20px 18px;
  text-align: center;
  background: linear-gradient(180deg, #1b2438, var(--bg));
  border-bottom: 1px solid #26324a;
}

.topbar h1 { margin: 0 0 6px; font-size: 1.6rem; }
.subtitle { margin: 0; color: var(--muted); font-size: 0.95rem; }

.container { max-width: 720px; margin: 0 auto; padding: 20px; }

.entry-form { display: flex; gap: 10px; margin-bottom: 18px; }

.entry-form input {
  flex: 1;
  padding: 12px 14px;
  border-radius: var(--radius);
  border: 1px solid #2c3a55;
  background: var(--panel);
  color: var(--text);
  font-size: 1rem;
}

.entry-form input:focus { outline: 2px solid var(--accent); border-color: transparent; }

button {
  border: none;
  border-radius: var(--radius);
  padding: 12px 18px;
  font-size: 1rem;
  cursor: pointer;
  background: var(--accent);
  color: #fff;
  transition: filter 0.15s ease;
}

button:hover { filter: brightness(1.12); }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.filters { display: flex; gap: 8px; }
.filters .filter { background: var(--panel); color: var(--muted); padding: 8px 14px; font-size: 0.9rem; }
.filters .filter.active { background: var(--accent); color: #fff; }
.counter { color: var(--muted); font-size: 0.9rem; }

.entry-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }

.entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--panel);
  border: 1px solid #24314a;
  border-radius: var(--radius);
  padding: 12px 14px;
}

.entry-main { display: flex; align-items: center; gap: 10px; flex: 1; cursor: pointer; }
.entry-text { overflow-wrap: anywhere; }
.entry.done .entry-text { text-decoration: line-through; color: var(--muted); }
.toggle { width: 18px; height: 18px; accent-color: var(--accent); }
.delete { background: transparent; color: var(--muted); font-size: 1rem; padding: 6px 10px; }
.delete:hover { color: var(--danger); }

.empty { color: var(--muted); text-align: center; padding: 24px 0; }
'''
)

JS_TEMPLATE = Template(
    '''/* $title — منطق التطبيق */
(function () {
  "use strict";

  var STORAGE_KEY = "$storage_key";
  var listEl = document.getElementById("entry-list");
  var formEl = document.getElementById("entry-form");
  var inputEl = document.getElementById("entry-input");
  var counterEl = document.getElementById("counter");
  var emptyEl = document.getElementById("empty-state");
  var template = document.getElementById("entry-template");
  var filterButtons = Array.prototype.slice.call(document.querySelectorAll(".filter"));
  var currentFilter = "all";

  function load() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      var data = raw ? JSON.parse(raw) : [];
      return Array.isArray(data) ? data : [];
    } catch (err) {
      return [];
    }
  }

  function save(items) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (err) {
      /* التخزين ممتلئ أو محظور — نتجاهل بهدوء */
    }
  }

  function visible(items) {
    if (currentFilter === "active") {
      return items.filter(function (item) { return !item.done; });
    }
    if (currentFilter === "done") {
      return items.filter(function (item) { return item.done; });
    }
    return items;
  }

  function render() {
    var items = load();
    var shown = visible(items);
    listEl.innerHTML = "";

    shown.forEach(function (item) {
      var node = template.content.cloneNode(true);
      var text = node.querySelector(".entry-text");
      var toggle = node.querySelector(".toggle");
      var del = node.querySelector(".delete");
      text.textContent = item.text;
      toggle.checked = !!item.done;
      if (item.done) { node.querySelector(".entry").classList.add("done"); }

      toggle.addEventListener("change", function () {
        item.done = toggle.checked;
        save(items);
        render();
      });

      del.addEventListener("click", function () {
        var index = items.indexOf(item);
        if (index > -1) { items.splice(index, 1); }
        save(items);
        render();
      });

      listEl.appendChild(node);
    });

    var active = items.filter(function (item) { return !item.done; }).length;
    counterEl.textContent = items.length + " عنصر (" + active + " غير منتهٍ)";
    emptyEl.style.display = shown.length ? "none" : "block";
  }

  formEl.addEventListener("submit", function (event) {
    event.preventDefault();
    var text = inputEl.value.trim();
    if (!text) { return; }
    var items = load();
    items.push({ id: Date.now(), text: text, done: false, created: new Date().toISOString() });
    save(items);
    inputEl.value = "";
    render();
  });

  filterButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      filterButtons.forEach(function (b) { b.classList.remove("active"); });
      button.classList.add("active");
      currentFilter = button.getAttribute("data-filter");
      render();
    });
  });

  render();
})();
'''
)

TEST_TEMPLATE = Template(
    '''"""فحوص أساسية لتطبيق الويب $title"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestWebAssets(unittest.TestCase):
    def test_files_exist(self):
        for name in ("index.html", "styles.css", "app.js", "README.md"):
            self.assertTrue((ROOT / name).exists(), f"missing {name}")

    def test_html_structure(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for marker in ('id="entry-form"', 'id="entry-list"', "app.js", 'dir="rtl"'):
            self.assertIn(marker, html)

    def test_js_persistence_hook(self):
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("localStorage", js)
        self.assertIn("render", js)

    def test_no_placeholder_text(self):
        for name in ("index.html", "app.js"):
            content = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("TODO", content)
            self.assertNotIn("Lorem ipsum", content)


if __name__ == "__main__":
    unittest.main()
'''
)


class WebAppGenerator(Generator):
    kind = "web_app"

    @staticmethod
    def _default_entity(spec: Spec) -> str:
        """اسم كيان مناسب للواجهة: عربي للطلبات العربية، إنجليزي لغيرها."""
        import re

        if re.search(r"[\u0600-\u06FF]", f"{spec.title} {spec.request}"):
            return "عنصر"
        return "item"

    def generate(self, spec: Spec) -> dict[str, str]:
        entity = spec.entities[0] if spec.entities else self._default_entity(spec)
        placeholder = f"اكتب {entity} جديداً..."
        storage_key = f"{spec.name}_items"

        readme = self.readme(
            spec,
            run=[
                "python3 -m http.server 8000",
                "# ثم افتح المتصفح على http://localhost:8000",
                "python3 -m unittest discover -s tests -t . -v",
            ],
            extra="## المزايا الإضافية\n"
            "- تخزين محلي (localStorage) — البيانات تبقى بعد إعادة التحميل\n"
            "- تصفية: الكل / غير منتهٍ / منتهٍ\n"
            "- تصميم عربي RTL متجاوب مع الجوال\n"
            "- بلا أي تبعيات أو عملية بناء\n\n",
        )

        return {
            "index.html": HTML_TEMPLATE.substitute(
                title=spec.title,
                description=spec.description,
                placeholder=placeholder,
            ),
            "styles.css": CSS_TEMPLATE.substitute(),
            "app.js": JS_TEMPLATE.substitute(title=spec.title, storage_key=storage_key),
            "README.md": readme,
            "tests/__init__.py": "",
            "tests/test_web_app.py": TEST_TEMPLATE.substitute(title=spec.title),
        }

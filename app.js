/* تطبيق ويب لمتابعة العادات اليومية — منطق التطبيق */
(function () {
  "use strict";

  var STORAGE_KEY = "web_app_items";
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

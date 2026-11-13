/* منصة بناء الأدوات — منطق الواجهة */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var state = { project: null, files: [], current: null, previewUrl: null };

  function toast(message, isError) {
    var el = $("toast");
    el.textContent = message;
    el.className = isError ? "toast err" : "toast";
    el.hidden = false;
    clearTimeout(el._timer);
    el._timer = setTimeout(function () { el.hidden = true; }, 3200);
  }

  function esc(text) {
    return String(text).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function api(path, options) {
    return fetch(path, options).then(function (res) {
      var type = res.headers.get("Content-Type") || "";
      if (type.indexOf("application/json") === -1) {
        if (!res.ok) { throw new Error("HTTP " + res.status); }
        return res.text();
      }
      return res.json().then(function (data) {
        if (!res.ok) { throw new Error(data.error || "HTTP " + res.status); }
        return data;
      });
    });
  }

  // ---------- الحالة العامة ----------
  function refreshStatus() {
    api("/api/status").then(function (data) {
      var badge = $("llm-badge");
      if (data.llm.enabled) {
        badge.textContent = "● LLM: " + data.llm.model;
        badge.className = "badge badge-on";
      } else {
        badge.textContent = "● المحرك المحلي (بلا مفتاح LLM)";
        badge.className = "badge badge-off";
      }
      var select = $("kind");
      if (select.options.length <= 1) {
        Object.keys(data.kinds).forEach(function (key) {
          var option = document.createElement("option");
          option.value = key;
          option.textContent = data.kinds[key];
          select.appendChild(option);
        });
      }
    }).catch(function () {
      $("llm-badge").textContent = "● تعذّر الاتصال بالخادم";
      $("llm-badge").className = "badge badge-off";
    });
  }

  function refreshProjects() {
    api("/api/projects").then(function (data) {
      var list = $("projects-list");
      if (!data.projects.length) {
        list.innerHTML = '<li class="muted">لا يوجد بعد.</li>';
      } else {
        list.innerHTML = data.projects.map(function (p) {
          return '<li data-project="' + esc(p.name) + '">' +
            '<strong>' + esc(p.name) + '</strong>' +
            '<span class="p-sub">' + p.files + ' ملف · ' + Math.round(p.size / 1024) + ' KB</span></li>';
        }).join("");
        Array.prototype.forEach.call(list.querySelectorAll("li[data-project]"), function (li) {
          li.addEventListener("click", function () { openProject(li.getAttribute("data-project")); });
        });
      }

      var history = $("history-list");
      if (!data.history.length) {
        history.innerHTML = '<li class="muted">لا يوجد سجل بعد.</li>';
      } else {
        history.innerHTML = data.history.slice(0, 12).map(function (h) {
          var when = new Date((h.timestamp || 0) * 1000).toLocaleString("ar", { hour12: false });
          return '<li data-request="' + esc(h.request) + '">' +
            '<span>' + esc(h.request) + '</span>' +
            '<span class="h-sub">' + esc(h.project) + ' · ' + when + '</span></li>';
        }).join("");
        Array.prototype.forEach.call(history.querySelectorAll("li[data-request]"), function (li) {
          li.addEventListener("click", function () {
            $("command").value = li.getAttribute("data-request");
            build();
          });
        });
      }
    }).catch(function () { /* تجاهل */ });
  }

  // ---------- البناء ----------
  function build() {
    var request = $("command").value.trim();
    if (!request) { toast("اكتب أمراً أولاً.", true); return; }

    var btn = $("build-btn");
    btn.disabled = true;
    $("build-btn").querySelector(".spinner").hidden = false;
    $("build-btn").querySelector(".btn-label").textContent = "جارٍ التوليد…";
    toast("جارٍ توليد المشروع…");

    api("/api/build", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request: request,
        kind: $("kind").value || null,
        provider: $("provider").value,
        verify: $("verify").checked
      })
    }).then(function (data) {
      state.project = data.project;
      state.files = data.files;
      state.previewUrl = data.preview;
      renderResult(data);
      toast(data.ok ? "✓ تم البناء والتحقق بنجاح" : "تم البناء — راجع نتائج التحقق");
      refreshProjects();
    }).catch(function (err) {
      toast("خطأ: " + err.message, true);
    }).finally(function () {
      btn.disabled = false;
      $("build-btn").querySelector(".spinner").hidden = true;
      $("build-btn").querySelector(".btn-label").textContent = "⚡ بناء المشروع";
    });
  }

  function renderResult(data) {
    $("placeholder").hidden = true;
    $("result").hidden = false;

    $("result-title").textContent = data.spec.title || data.project;
    $("result-sub").textContent = data.kind_label + " · " + data.project +
      " · " + data.files.length + " ملف · " + data.elapsed + " ثانية · مصدر التخطيط: " + (data.spec.source || "-");

    var row = $("verify-row");
    if (!data.verification.length) {
      row.innerHTML = '<span class="chip-verify">لم يُشغَّل أي فحص</span>';
    } else {
      row.innerHTML = data.verification.map(function (v) {
        return '<span class="chip-verify ' + (v.ok ? "ok" : "fail") + '">' +
          (v.ok ? "✓" : "✕") + " " + esc(v.name) + "</span>";
      }).join("");
    }

    var run = [
      "# التشغيل",
      data.entrypoint,
      "",
      "# التحقق",
    ].concat(data.verification.map(function (v) {
      return (v.ok ? "✓ " : "✕ ") + v.name + (v.output ? "\n" + v.output.split("\n").slice(0, 6).join("\n") : "");
    }));
    if (data.notes && data.notes.length) {
      run.push("", "# ملاحظات");
      run = run.concat(data.notes);
    }
    run.push("", "# الملفات (" + data.files.length + ")");
    run = run.concat(data.files.map(function (f) { return "  " + f.path + "  (" + f.size + "B)"; }));
    $("run-view").textContent = run.join("\n");

    var previewTab = $("preview-tab");
    if (data.preview) {
      previewTab.hidden = false;
      $("preview-frame").src = data.preview;
    } else {
      previewTab.hidden = true;
      $("preview-frame").src = "about:blank";
    }

    renderTree(data.files);
    $("code-view").textContent = "";
    $("code-path").textContent = "اختر ملفاً لعرض محتواه";
    state.current = null;
  }

  function renderTree(files) {
    var tree = $("file-tree");
    tree.innerHTML = files.map(function (f) {
      return '<li data-path="' + esc(f.path) + '">' + esc(f.path) + "</li>";
    }).join("");
    Array.prototype.forEach.call(tree.querySelectorAll("li"), function (li) {
      li.addEventListener("click", function () {
        Array.prototype.forEach.call(tree.querySelectorAll("li"), function (x) { x.classList.remove("active"); });
        li.classList.add("active");
        openFile(li.getAttribute("data-path"));
      });
    });
  }

  function openFile(path) {
    if (!state.project) { return; }
    api("/api/files?name=" + encodeURIComponent(state.project) + "&path=" + encodeURIComponent(path))
      .then(function (data) {
        state.current = data.content;
        $("code-path").textContent = path;
        $("code-view").textContent = data.content;
      })
      .catch(function (err) { toast("تعذّر فتح الملف: " + err.message, true); });
  }

  function openProject(name) {
    $("command").value = "";
    api("/api/files?name=" + encodeURIComponent(name)).then(function (data) {
      state.project = name;
      state.files = data.files;
      $("placeholder").hidden = true;
      $("result").hidden = false;
      $("result-title").textContent = name;
      $("result-sub").textContent = "مشروع محفوظ (" + data.files.length + " ملف)";
      $("verify-row").innerHTML = '<span class="chip-verify">مشروع محفوظ</span>';
      $("run-view").textContent = "افتح مجلد المشروع:\n" + name + "\n\n# الملفات\n" +
        data.files.map(function (f) { return "  " + f.path; }).join("\n");
      renderTree(data.files);
      $("code-view").textContent = "";
      $("code-path").textContent = "اختر ملفاً لعرض محتواه";
      var hasWeb = data.files.some(function (f) { return f.path === "index.html"; });
      $("preview-tab").hidden = !hasWeb;
      if (hasWeb) { $("preview-frame").src = "/preview/" + encodeURIComponent(name) + "/index.html"; }
    }).catch(function (err) { toast(err.message, true); });
  }

  // ---------- الأحداث ----------
  $("build-btn").addEventListener("click", build);
  $("command").addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { build(); }
  });
  Array.prototype.forEach.call(document.querySelectorAll(".chip[data-example]"), function (chip) {
    chip.addEventListener("click", function () {
      $("command").value = chip.getAttribute("data-example");
      build();
    });
  });
  Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (tab) {
    tab.addEventListener("click", function () {
      Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (t) { t.classList.remove("active"); });
      Array.prototype.forEach.call(document.querySelectorAll(".tab-panel"), function (p) { p.classList.remove("active"); });
      tab.classList.add("active");
      $("tab-" + tab.getAttribute("data-tab")).classList.add("active");
    });
  });
  $("download-btn").addEventListener("click", function () {
    if (!state.project) { toast("لا يوجد مشروع للتحميل.", true); return; }
    window.location.href = "/api/download?name=" + encodeURIComponent(state.project);
  });
  $("copy-btn").addEventListener("click", function () {
    var text = $("command").value;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function () { toast("نُسخ الأمر"); });
    } else {
      toast("المتصفح لا يدعم النسخ التلقائي.", true);
    }
  });
  $("copy-code").addEventListener("click", function () {
    if (state.current && navigator.clipboard) {
      navigator.clipboard.writeText(state.current).then(function () { toast("نُسخ محتوى الملف"); });
    }
  });

  $("settings-btn").addEventListener("click", function () { $("settings-modal").hidden = false; });
  $("close-settings").addEventListener("click", function () { $("settings-modal").hidden = true; });
  $("save-settings").addEventListener("click", function () {
    api("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: $("api-key").value.trim(),
        model: $("model-name").value.trim() || null
      })
    }).then(function (data) {
      $("settings-msg").textContent = data.llm_enabled
        ? "✓ تم التفعيل — النموذج اللغوي جاهز."
        : "حُفظ المفتاح. تعذّر تفعيل النموذج — تحقق من صحة المفتاح.";
      toast(data.llm_enabled ? "✓ تم تفعيل النموذج اللغوي" : "تعذّر التفعيل", !data.llm_enabled);
      refreshStatus();
    }).catch(function (err) { toast("خطأ: " + err.message, true); });
  });

  refreshStatus();
  refreshProjects();
})();

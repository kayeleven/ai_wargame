(() => {
  "use strict";
  const storePrefix = "lm-workspace:";
  const fields = form => [...form.elements].filter(el => el.name && el.type !== "hidden");
  const values = form => Object.fromEntries(fields(form).map(el => [el.name, el.value]));
  const commandValues = form => Object.fromEntries(
    [...form.elements].filter(el => el.name && el.name !== "csrf_token").map(el => [el.name, el.value])
  );
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const root = () => document.querySelector("[data-workspace]");
  const user = () => document.body.dataset.userId || "anonymous";
  const storageKey = form => `${storePrefix}${user()}:${root()?.dataset.workspace}:${form.dataset.editor}`;

  function status(message, kind = "notice") {
    const node = document.querySelector("#workspace-status");
    if (!node) return;
    node.className = kind;
    node.setAttribute("role", kind.includes("error") ? "alert" : "status");
    node.textContent = message;
    node.focus?.();
  }

  function mark(form) {
    if (!form.dataset.editor) return;
    const dirty = !same(values(form), JSON.parse(form.dataset.baseline || "{}"));
    form.dataset.dirty = String(dirty);
    if (dirty) {
      sessionStorage.setItem(storageKey(form), JSON.stringify({
        values: values(form), expectedVersion: form.elements.namedItem("expected_version")?.value
      }));
    } else {
      sessionStorage.removeItem(storageKey(form));
    }
  }

  function setValues(form, saved) {
    for (const [name, value] of Object.entries(saved || {})) {
      const control = form.elements.namedItem(name);
      if (control && !["csrf_token", "key"].includes(name)) control.value = value;
    }
  }

  function initializeForms(preserved = {}, cleanEditor = null) {
    const priorUser = sessionStorage.getItem("lm-workspace-user");
    if (priorUser && priorUser !== user()) {
      for (let index = sessionStorage.length - 1; index >= 0; index--) {
        const key = sessionStorage.key(index);
        if (key?.startsWith(storePrefix)) sessionStorage.removeItem(key);
      }
    }
    sessionStorage.setItem("lm-workspace-user", user());
    document.querySelectorAll("form[data-editor]").forEach(form => {
      const current = values(form);
      form.dataset.baseline = JSON.stringify(current);
      let savedState = preserved[form.dataset.editor];
      let saved = savedState?.values;
      let retained = null;
      if (form.dataset.editor === cleanEditor) {
        sessionStorage.removeItem(storageKey(form));
      } else if (!saved) {
        try {
          retained = JSON.parse(sessionStorage.getItem(storageKey(form)) || "null");
          savedState = retained;
          saved = retained?.values;
        }
        catch { saved = null; }
      }
      if (saved) {
        setValues(form, saved);
        const expected = form.elements.namedItem("expected_version");
        if (expected && savedState?.expectedVersion) expected.value = savedState.expectedVersion;
      }
      if (retained?.pending) {
        setValues(form, retained.pending);
        const key = form.elements.namedItem("key");
        if (key && retained.pending.key) key.value = retained.pending.key;
        root().dataset.unresolved = "true";
        form.dataset.retryPending = "true";
        const submit = form.querySelector('[type="submit"],button:not([type])');
        if (submit) submit.textContent = "Retry save";
        status("A previous save has an unknown outcome. Retry save uses its original operation identity.", "notice error");
      }
      mark(form);
    });
  }

  function dirtyEditors(except = null) {
    return [...document.querySelectorAll("form[data-editor][data-dirty=true]")]
      .filter(form => form !== except);
  }
  const dirtyAdminForms = () => [...document.querySelectorAll('form[data-admin-form][data-dirty="true"]')];

  function editorName(form) {
    return form.dataset.editor.replaceAll("-", " ");
  }

  function showChoice(anchor, message, onDiscard) {
    document.querySelector("[data-inline-confirm]")?.remove();
    const box = document.createElement("div");
    box.dataset.inlineConfirm = "true";
    box.className = "notice";
    box.setAttribute("role", "alertdialog");
    box.setAttribute("aria-label", "Unsaved changes");
    box.innerHTML = `<p>${message}</p><div class="button-row"><button type="button" data-keep>Keep editing</button><button type="button" data-discard>Discard changes</button></div>`;
    anchor.after(box);
    box.querySelector("[data-keep]").addEventListener("click", () => { box.remove(); anchor.focus(); });
    box.querySelector("[data-discard]").addEventListener("click", () => { box.remove(); onDiscard(); });
    box.querySelector("[data-keep]").focus();
  }

  async function submitWorkspace(form) {
    if (root()?.dataset.unresolved === "true" && form.dataset.retryPending !== "true") {
      status("Resolve the uncertain operation before starting another save.", "notice error");
      return;
    }
    if (form.dataset.packageCommand !== undefined) {
      const dirty = dirtyEditors();
      if (dirty.length) {
        status(`Save or discard these editors first: ${dirty.map(editorName).join(", ")}.`, "notice error");
        dirty[0].querySelector("textarea,input,select")?.focus();
        return;
      }
    }
    const submittedEditor = form.dataset.editor;
    const preserved = Object.fromEntries(dirtyEditors(form).map(item => [item.dataset.editor, {
      values: values(item), expectedVersion: item.elements.namedItem("expected_version")?.value
    }]));
    form.setAttribute("aria-busy", "true");
    [...form.elements].forEach(control => { if (control.type === "submit") control.disabled = true; });
    try {
      const response = await fetch(form.action, {method:"POST", body:new FormData(form), headers:{"Accept":"text/html"}});
      const html = await response.text();
      const parsed = new DOMParser().parseFromString(html, "text/html");
      if (!parsed.querySelector("[data-workspace]")) throw new Error("Unexpected response");
      if (submittedEditor) sessionStorage.removeItem(storageKey(form));
      document.body.innerHTML = parsed.body.innerHTML;
      initializeForms(preserved, submittedEditor);
      const alert = document.querySelector("[role=alert]");
      if (alert) alert.focus?.(); else status("Saved. The submitted package is unchanged.");
    } catch {
      root().dataset.unresolved = "true";
      form.dataset.retryPending = "true";
      form.removeAttribute("aria-busy");
      [...form.elements].forEach(control => { if (control.type === "submit") { control.disabled = false; control.textContent = "Retry save"; } });
      status("Save outcome unknown. Retry save may perform the original save if it did not complete. Other saves are paused in this tab.", "notice error");
      if (submittedEditor) sessionStorage.setItem(
        storageKey(form),
        JSON.stringify({values:values(form), pending:commandValues(form)})
      );
    }
  }

  document.addEventListener("input", event => {
    const form = event.target.closest("form[data-editor]");
    if (form) mark(form);
    const admin = event.target.closest("form[data-admin-form]");
    if (admin) admin.dataset.dirty = String(!same(values(admin), JSON.parse(admin.dataset.baseline)));
  });
  document.addEventListener("change", event => {
    const form = event.target.closest("form[data-editor]");
    if (form) mark(form);
    const admin = event.target.closest("form[data-admin-form]");
    if (admin) admin.dataset.dirty = String(!same(values(admin), JSON.parse(admin.dataset.baseline)));
  });
  document.addEventListener("submit", event => {
    const form = event.target;
    if (form.matches("[data-workspace-form]")) {
      event.preventDefault();
      submitWorkspace(form);
      return;
    }
    if (form.matches("[data-admin-form]")) form.dataset.dirty = "false";
    const dirty = dirtyEditors();
    if (dirty.length && form.matches("[data-guard-navigation]")) {
      event.preventDefault();
      showChoice(form, "Leaving will discard unsaved workspace changes.", () => form.submit());
    }
  });
  document.addEventListener("click", event => {
    const cancel = event.target.closest("[data-cancel-editor]");
    if (cancel) {
      const form = cancel.closest("form[data-editor]");
      if (form.dataset.dirty !== "true") return;
      showChoice(cancel, `Discard unsaved changes in ${editorName(form)}?`, () => {
        setValues(form, JSON.parse(form.dataset.baseline));
        mark(form);
        form.querySelector("textarea,input,select")?.focus();
      });
      return;
    }
    const link = event.target.closest("a[href]");
    if (link && (dirtyEditors().length || dirtyAdminForms().length) && !link.href.startsWith("javascript:")) {
      event.preventDefault();
      showChoice(link, "Leaving will discard unsaved workspace changes.", () => { location.href = link.href; });
    }
  });
  window.addEventListener("beforeunload", event => {
    if (dirtyEditors().length || dirtyAdminForms().length || root()?.dataset.unresolved === "true") { event.preventDefault(); event.returnValue = ""; }
  });
  document.querySelectorAll('form[action^="/admin"]:not([data-workspace-form])').forEach(form => {
    form.dataset.adminForm = "true";
    form.dataset.baseline = JSON.stringify(values(form));
    form.dataset.dirty = "false";
  });
  initializeForms();
})();

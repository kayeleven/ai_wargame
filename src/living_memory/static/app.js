(() => {
  "use strict";
  const prefix = "lm-workspace:";
  const memory = new Map();
  const workspace = () => document.querySelector("[data-workspace]");
  const user = () => document.body.dataset.userId || "anonymous";
  const controls = form => [...form.elements].filter(item => item.name && item.type !== "hidden");
  const formValues = form => Object.fromEntries(controls(form).map(item => [item.name, item.value]));
  const equal = (one, two) => JSON.stringify(one) === JSON.stringify(two);
  const editorId = form => form.dataset.editor;
  const commandScope = form => ["operation", "action_id", "amendment_id", "effective_version", "order"].map(name => form.elements.namedItem(name)?.value || "").join(":");
  const keyFor = form => `${prefix}${user()}:${workspace()?.dataset.workspace}:${editorId(form) || `command:${commandScope(form)}`}`;
  const stateKey = form => `${keyFor(form)}:pending`;
  const unresolvedKey = () => `${prefix}${user()}:${workspace()?.dataset.workspace}:unresolved-command`;

  function read(key) { try { const stored = sessionStorage.getItem(key); return stored === null ? memory.get(key) || null : JSON.parse(stored); } catch { return memory.get(key) || null; } }
  function write(key, value) { memory.set(key, value); try { sessionStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; } }
  function erase(key) { memory.delete(key); try { sessionStorage.removeItem(key); } catch { /* memory fallback */ } }
  function recoveryWarning() {
    if (document.querySelector("[data-storage-warning]")) return;
    const notice = document.createElement("p"); notice.dataset.storageWarning = "true"; notice.className = "notice error";
    notice.textContent = "Draft recovery is available only while this page remains open.";
    document.querySelector("#workspace-status")?.after(notice);
  }
  function save(key, value) { if (!write(key, value)) recoveryWarning(); }
  function announce(message, kind = "notice", focus = false) {
    const target = document.querySelector("#workspace-status"); if (!target) return;
    target.className = kind; target.setAttribute("role", kind.includes("error") ? "alert" : "status"); target.tabIndex = -1; target.textContent = message;
    if (focus) target.focus();
  }
  function applyValues(form, saved) { Object.entries(saved || {}).forEach(([name, value]) => { const item = form.elements.namedItem(name); if (item && !["csrf_token", "key", "operation", "expected_version"].includes(name)) item.value = value; }); }
  function setBaseline(form, value = formValues(form)) { form.dataset.baseline = JSON.stringify(value); form.dataset.dirty = "false"; }
  const authoritativeKey = name => `authoritative${name.split("_").map(part => part[0].toUpperCase() + part.slice(1)).join("")}`;
  function rememberAuthoritative(form, incoming) {
    form.dataset.authoritative = JSON.stringify(formValues(incoming));
    for (const name of ["expected_version", "key", "csrf_token"]) {
      const control = incoming.elements.namedItem(name);
      if (control) form.dataset[authoritativeKey(name)] = control.value;
    }
  }
  function discardToAuthoritative(form) {
    const values = JSON.parse(form.dataset.authoritative || form.dataset.baseline || "{}");
    applyValues(form, values);
    for (const name of ["expected_version", "key", "csrf_token"]) {
      const value = form.dataset[authoritativeKey(name)];
      const control = form.elements.namedItem(name); if (control && value != null) control.value = value;
    }
    setBaseline(form, values); erase(keyFor(form));
  }
  function mark(form) {
    if (!editorId(form)) return;
    const authored = formValues(form), dirty = !equal(authored, JSON.parse(form.dataset.baseline || "{}"));
    form.dataset.dirty = String(dirty);
    if (dirty) save(keyFor(form), { authored, expectedVersion: form.elements.namedItem("expected_version")?.value }); else erase(keyFor(form));
  }
  function dirtyEditors(except) { return [...document.querySelectorAll("form[data-editor][data-dirty=true]")].filter(form => form !== except); }
  function discardDirtyRecovery() { dirtyEditors().forEach(form => erase(keyFor(form))); }
  const dirtyAdminForms = () => [...document.querySelectorAll('form[data-admin-form][data-dirty="true"]')];
  function markAdmin(form) { form.dataset.dirty = String(!equal(formValues(form), JSON.parse(form.dataset.baseline || "{}"))); }
  function editorLabel(form) { return editorId(form).replaceAll("-", " "); }
  function freeze(form) {
    const values = {}; [...form.elements].forEach(control => { if (control.name && control.name !== "csrf_token") values[control.name] = control.value; });
    return { values, authored: formValues(form), editor: editorId(form), operation: form.elements.namedItem("operation")?.value, key: form.elements.namedItem("key")?.value, action: form.action };
  }
  function fillFrozen(form, frozen) { Object.entries(frozen.values).forEach(([name, value]) => { const item = form.elements.namedItem(name); if (item) item.value = value; }); }
  function restore(form) {
    const saved = read(keyFor(form)), pending = read(stateKey(form));
    if (saved?.authored) { applyValues(form, saved.authored); const version = form.elements.namedItem("expected_version"); if (version && saved.expectedVersion) version.value = saved.expectedVersion; mark(form); }
    if (pending) { form.dataset.pending = "true"; workspace().dataset.unresolved = "true"; const button = form.querySelector("button[type=submit],button:not([type])"); if (button) button.textContent = "Retry save"; announce("A previous save has an unknown outcome. Retry uses the exact original save.", "notice error", true); }
  }
  function clearPending(form) { erase(stateKey(form)); const unresolved = read(unresolvedKey()); if (!unresolved || unresolved.state === stateKey(form)) erase(unresolvedKey()); form.dataset.pending = ""; const button = form.querySelector("button[type=submit],button:not([type])"); if (button?.dataset.defaultLabel) button.textContent = button.dataset.defaultLabel; }
  function retainPending(form, frozen) { save(stateKey(form), frozen); save(unresolvedKey(), { state: stateKey(form), frozen }); }
  function restoreOrphanedCommand() {
    const unresolved = read(unresolvedKey()); if (!unresolved?.frozen || document.querySelector("form[data-pending-recovery]")) return;
    const frozen = unresolved.frozen;
    const matching = [...document.querySelectorAll("form[data-workspace-form]")].find(form => form.elements.namedItem("operation")?.value === frozen.operation && stateKey(form) === unresolved.state);
    if (matching) return;
    const panel = document.createElement("section"); panel.className = "notice error"; panel.dataset.pendingRecovery = "true"; panel.setAttribute("role", "alert");
    panel.innerHTML = `<p>A previous ${String(frozen.operation).replaceAll("_", " ")} has an unknown outcome.</p>`;
    const form = document.createElement("form"); form.method = "post"; form.action = frozen.action; form.dataset.workspaceForm = "true"; form.dataset.packageCommand = "true"; form.dataset.pendingRecovery = "true"; form.dataset.pending = "true";
    for (const [name, value] of Object.entries(frozen.values)) { const input = document.createElement("input"); input.type = "hidden"; input.name = name; input.value = value; form.append(input); }
    const csrf = document.createElement("input"); csrf.type = "hidden"; csrf.name = "csrf_token"; csrf.value = document.querySelector('[name="csrf_token"]')?.value || ""; form.append(csrf);
    const button = document.createElement("button"); button.type = "submit"; button.textContent = "Retry original operation"; form.append(button); panel.append(form); document.querySelector("#workspace-status")?.after(panel);
    workspace().dataset.unresolved = "true"; form.dataset.initialized = "true";
  }
  function initialize() { document.querySelectorAll("form[data-workspace-form]").forEach(form => { if (form.dataset.initialized) return; form.dataset.initialized = "true"; const button = form.querySelector("button[type=submit],button:not([type])"); if (button) button.dataset.defaultLabel = button.textContent; if (editorId(form)) setBaseline(form); restore(form); }); restoreOrphanedCommand(); }
  function clearForOtherUser() {
    try { const prior = sessionStorage.getItem("lm-workspace-user"); if (prior && prior !== user()) for (let index = sessionStorage.length - 1; index >= 0; index--) { const key = sessionStorage.key(index); if (key?.startsWith(`${prefix}${prior}:`)) sessionStorage.removeItem(key); } sessionStorage.setItem("lm-workspace-user", user()); } catch { recoveryWarning(); }
  }
  function choice(anchor, message, discard) {
    document.querySelector("[data-inline-confirm]")?.remove();
    const box = document.createElement("section"); box.dataset.inlineConfirm = "true"; box.className = "notice"; box.tabIndex = -1; box.setAttribute("role", "alertdialog"); box.setAttribute("aria-modal", "true"); box.setAttribute("aria-label", "Unsaved changes");
    box.innerHTML = `<p>${message}</p><div class="button-row"><button type="button" data-keep>Keep editing</button><button type="button" data-discard>Discard changes</button></div>`;
    anchor.after(box); const close = () => { box.remove(); anchor.focus(); };
    box.querySelector("[data-keep]").addEventListener("click", close); box.querySelector("[data-discard]").addEventListener("click", () => { box.remove(); discard(); });
    box.addEventListener("keydown", event => { if (event.key === "Escape") { event.preventDefault(); close(); } }); box.querySelector("[data-keep]").focus();
  }
  function capturePosition() { const active = document.activeElement; return { x: window.scrollX, y: window.scrollY, id: active?.id, name: active?.name, editor: active?.closest("form[data-editor]")?.dataset.editor, start: active?.selectionStart, end: active?.selectionEnd }; }
  function restorePosition(position) { window.scrollTo(position.x, position.y); const editor = position.editor ? `form[data-editor="${CSS.escape(position.editor)}"] ` : ""; const item = position.id ? document.getElementById(position.id) : document.querySelector(`${editor}[name="${CSS.escape(position.name || "")}"]`); if (item) { item.focus(); if (item.setSelectionRange && position.start != null) item.setSelectionRange(position.start, position.end); } }
  function addUnavailableRecovery(form) {
    if (form.querySelector("[data-unavailable-recovery]")) return;
    form.querySelectorAll("textarea,input:not([type=hidden]),select,button[type=submit],button:not([type])").forEach(control => { control.disabled = true; });
    const panel = document.createElement("section"); panel.dataset.unavailableRecovery = "true"; panel.className = "notice error"; panel.innerHTML = "<p>This editor is no longer available. Copy your text before discarding it.</p>";
    const copy = document.createElement("button"); copy.type = "button"; copy.textContent = "Copy retained text"; copy.addEventListener("click", async () => { const text = controls(form).map(item => item.value).filter(Boolean).join("\n"); await navigator.clipboard.writeText(text); announce("Retained text copied."); });
    const discard = document.createElement("button"); discard.type = "button"; discard.textContent = "Discard retained text"; discard.addEventListener("click", () => { erase(keyFor(form)); form.remove(); });
    panel.append(copy, discard); form.append(panel);
  }
  function replaceCleanRegions(parsed, submitted) {
    const position = capturePosition();
    const incomingNames = new Set(), dirty = [...document.querySelectorAll("form[data-editor][data-dirty=true]")], grafted = new Set();
    const origins = new Map(dirty.map(form => [form, form.closest("[data-workspace-region]")?.dataset.workspaceRegion]));
    parsed.querySelectorAll("[data-workspace-region]").forEach(next => {
      const name = next.dataset.workspaceRegion; incomingNames.add(name);
      const current = document.querySelector(`[data-workspace-region="${CSS.escape(name)}"]`); if (!current) return;
      const replacement = next.cloneNode(true);
      dirty.forEach(form => {
        const incoming = replacement.querySelector(`form[data-editor="${CSS.escape(editorId(form))}"]`);
        if (incoming) { rememberAuthoritative(form, incoming); incoming.replaceWith(form); grafted.add(form); }
      });
      current.replaceWith(replacement);
    });
    dirty.filter(form => !grafted.has(form)).forEach(form => {
      const destination = document.querySelector(`[data-workspace-region="${CSS.escape(origins.get(form) || "")}"]`);
      if (destination) { addUnavailableRecovery(form); destination.append(form); grafted.add(form); }
    });
    document.querySelectorAll("[data-workspace-region]").forEach(current => {
      if (incomingNames.has(current.dataset.workspaceRegion)) return;
      const retained = current.querySelectorAll("form[data-editor][data-dirty=true]");
      if (!retained.length) { current.remove(); return; }
      retained.forEach(addUnavailableRecovery);
    });
    dirty.filter(form => !grafted.has(form) && form.isConnected).forEach(addUnavailableRecovery);
    initialize(); if (submitted?.matches?.("form[data-editor]") && submitted.isConnected) mark(submitted); workspace().dataset.refreshPending = ""; restorePosition(position);
  }
  function incomingEditor(parsed, id) { return parsed?.querySelector(`form[data-editor="${CSS.escape(id || "")}"]`); }
  function freshToken(form, parsed) { const next = incomingEditor(parsed, editorId(form)); ["expected_version", "key", "csrf_token"].forEach(name => { const from = next?.elements.namedItem(name), to = form.elements.namedItem(name); if (from && to) to.value = from.value; }); return next; }
  function applyConflictCurrent(form, current) {
    if (!current || typeof current !== "object") return;
    if (current.body && typeof current.body === "object") applyValues(form, {...current.body, owner_user_id: current.owner_user_id || ""});
    else applyValues(form, current);
  }
  function showConflict(form, payload, frozen) {
    const panel = document.createElement("section"); panel.className = "notice error conflict-resolution"; panel.dataset.conflict = "true"; panel.tabIndex = -1;
    const documentFromResponse = payload.html ? new DOMParser().parseFromString(payload.html, "text/html") : null;
    const conflict = payload.conflict || {}, display = payload.conflict_display || {};
    if (frozen.operation === "action" && (!conflict.current || conflict.current.removed)) {
      if (documentFromResponse) replaceCleanRegions(documentFromResponse, null);
      const retained = document.querySelector(`form[data-editor="${CSS.escape(frozen.editor || "")}"]`);
      if (retained) addUnavailableRecovery(retained);
      announce("This action was removed. Your attempted text is retained for copy or discard.", "notice error", true);
      return;
    }
    const escape = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    const label = value => {
      if (value == null || value === "") return "(empty)";
      if (typeof value === "string") return escape(value);
      if (typeof value !== "object") return escape(value);
      return Object.entries(value).filter(([name]) => !["action_id", "owner_user_id", "key", "expected_version"].includes(name)).map(([name, item]) => `${escape(name.replaceAll("_", " "))}: ${typeof item === "object" ? label(item) : escape(item)}`).join("\n") || "(empty)";
    };
    const displayLabel = item => item ? `${item.state === "removed" ? "(removed)\n" : item.state === "missing" ? "(missing)\n" : ""}${item.fields.map(field => `${escape(field.label)}: ${field.empty ? "(empty)" : escape(field.value)}`).join("\n") || "(empty)"}` : null;
    const editableText = ["intention", "action", "comment"].includes(frozen.operation);
    const buttons = editableText ? `<button type="button" data-choice="current">Use current</button><button type="button" data-choice="mine">Save mine</button><button type="button" data-choice="combined">Save combined</button>` : `<button type="button" data-choice="review">Review current state and renew this operation</button>`;
    panel.innerHTML = `<h3>Edit conflict</h3><p>Resolve the saved-value conflict</p><dl><dt>Base</dt><dd><pre>${displayLabel(display.base) || label(conflict.base)}</pre></dd><dt>Current</dt><dd><pre>${displayLabel(display.current) || label(conflict.current)}</pre></dd><dt>Mine</dt><dd><pre>${displayLabel(display.mine) || label(conflict.mine)}</pre></dd></dl><div class="button-row">${buttons}</div>`;
    panel.querySelectorAll("[data-choice]").forEach(button => button.addEventListener("click", () => {
      const mode = button.dataset.choice;
      if (mode === "review") { if (documentFromResponse) replaceCleanRegions(documentFromResponse, null); panel.remove(); announce("Current saved state loaded. Review it before renewing the operation.", "notice", true); return; }
      if (mode === "current") { applyConflictCurrent(form, conflict.current); if (documentFromResponse) freshToken(form, documentFromResponse); setBaseline(form); delete form.dataset.authoritative; erase(keyFor(form)); panel.remove(); announce("Current saved value loaded.", "notice", true); return; }
      fillFrozen(form, frozen); const version = form.elements.namedItem("expected_version"); if (version && payload.current_version != null) version.value = payload.current_version; const key = form.elements.namedItem("key"); if (key) key.value = crypto.randomUUID(); panel.remove(); mark(form);
      if (mode === "combined") { announce("Edit the combined value, then save it with the current revision.", "notice", true); form.querySelector("textarea,input,select")?.focus(); return; }
      submit(form);
    }));
    form.append(panel); panel.focus();
  }
  function showValidation(form, payload) {
    form.querySelector("[data-validation-errors]")?.remove();
    const panel = document.createElement("section"); panel.dataset.validationErrors = "true"; panel.className = "notice error"; panel.setAttribute("role", "alert"); panel.tabIndex = -1;
    const errors = payload?.errors || [];
    panel.innerHTML = `<h3>Please check your input</h3><ul>${errors.map(error => `<li>${String(error.message).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</li>`).join("")}</ul>`;
    for (const error of errors) {
      const described = [...form.querySelectorAll("[aria-describedby]")].find(item => item.getAttribute("aria-describedby")?.startsWith(`error-${error.field}`));
      const target = described ? document.getElementById(described.getAttribute("aria-describedby")) : null;
      if (target) target.textContent = error.message;
    }
    form.prepend(panel); panel.focus(); mark(form);
  }
  const classify = response => [401, 403, 404].includes(response.status) ? "rejected" : response.status >= 500 ? "uncertain" : response.status === 409 ? "conflict" : response.status === 422 ? "validation" : response.ok ? "acknowledged" : "uncertain";
  const success = operation => ({intention:"Overall intention saved.",action:"Action saved.",comment:"Comment added.",submit:"Turn package submitted.",amend:"Amendment proposed.",remove:"Action removed.",reorder:"Action order updated.",decide:"Amendment decision recorded."})[operation] || "Saved.";
  async function refresh(form, destination = location.href) {
    try { const response = await fetch(destination, { headers: { Accept:"text/html", "X-Workspace-Enhanced":"1" } }); if (!response.ok) throw new Error(); const parsed = new DOMParser().parseFromString(await response.text(), "text/html"); replaceCleanRegions(parsed, form); freshToken(form, parsed); if (form.isConnected && editorId(form)) mark(form); workspace().dataset.refreshPending = ""; document.querySelector("[data-retry-refresh]")?.remove(); }
    catch {
      workspace().dataset.refreshPending = "true";
      announce("Saved; current view could not be refreshed.", "notice error", true);
      document.querySelector("[data-retry-refresh]")?.remove(); const retry = document.createElement("button"); retry.type = "button"; retry.dataset.retryRefresh = "true"; retry.textContent = "Retry refresh"; retry.addEventListener("click", () => refresh(form, destination)); document.querySelector("#workspace-status")?.after(retry);
    }
  }
  async function submit(form, retry = false) {
    if (form.dataset.packageCommand !== undefined && workspace()?.dataset.refreshPending === "true") { announce("Refresh the saved workspace before using a package command.", "notice error", true); return; }
    if (form.dataset.packageCommand !== undefined && dirtyEditors().length) { const dirty = dirtyEditors(); announce(`Save or discard these editors first: ${dirty.map(editorLabel).join(", ")}.`, "notice error", true); dirty[0].querySelector("textarea,input,select")?.focus(); return; }
    if (workspace()?.dataset.inflight) { announce("Wait for the current save to finish before starting another operation.", "notice error", true); return; }
    if (workspace()?.dataset.unresolved === "true" && !form.dataset.pending) { announce("Resolve the uncertain save before starting another operation.", "notice error", true); return; }
    const frozen = retry ? read(stateKey(form)) : freeze(form); if (!frozen) return;
    workspace().dataset.inflight = editorId(form) || keyFor(form); form.dataset.inflight = "true"; form.setAttribute("aria-busy", "true"); form.querySelectorAll("button[type=submit],button:not([type])").forEach(button => { button.disabled = true; });
    try {
      const body = new FormData(form); if (retry) Object.entries(frozen.values).forEach(([name, value]) => body.set(name, value));
      const response = await fetch(frozen.action, {method:"POST", body, redirect:"follow", headers:{Accept:"application/vnd.living-memory.workspace+json, text/html", "X-Workspace-Enhanced":"1"}});
      const kind = classify(response);
      if (kind === "rejected") {
        if (retry) { form.dataset.pending = "true"; workspace().dataset.unresolved = "true"; announce("The retry was rejected; the original save outcome is still unknown. The exact original command remains available for reconciliation.", "notice error", true); return; }
        clearPending(form); workspace().dataset.unresolved = ""; announce("Save was rejected; your draft remains available to edit.", "notice error", true); return;
      }
      const type = response.headers.get("content-type") || "", enhancedType = type.toLowerCase().startsWith("application/vnd.living-memory.workspace+json"); const payload = type.includes("json") ? await response.json() : null;
      if (kind === "uncertain") throw new Error();
      if (kind === "conflict") {
        if (payload?.outcome === "key_conflict") {
          clearPending(form); form.dataset.pending = ""; workspace().dataset.unresolved = "";
          announce("This save identity was already used for different content. Review your draft and start a new save.", "notice error", true);
          const key = form.elements.namedItem("key"); if (key) key.value = crypto.randomUUID();
          mark(form); return;
        }
        clearPending(form); form.dataset.pending = ""; workspace().dataset.unresolved = ""; showConflict(form, payload || {}, frozen); return;
      }
      if (kind === "validation") { clearPending(form); workspace().dataset.unresolved = ""; showValidation(form, payload || {}); return; }
      const editorMatches = frozen.editor === "new-action" ? payload?.editor?.startsWith("action-") : payload?.editor === (frozen.editor || null);
      if (!enhancedType || !payload || payload.outcome !== "committed" || payload.operation !== frozen.operation || payload.key !== frozen.key || !editorMatches || typeof payload.refresh !== "string" || !payload.refresh) throw new Error();
      clearPending(form); form.dataset.pending = ""; workspace().dataset.unresolved = "";
      const acknowledgedAuthoredKey = keyFor(form);
      if (frozen.editor === "new-action" && payload?.editor?.startsWith("action-")) {
        const actionId = payload.editor.slice("action-".length);
        form.dataset.editor = payload.editor;
        let action = form.elements.namedItem("action_id");
        if (!action) { action = document.createElement("input"); action.type = "hidden"; action.name = "action_id"; form.append(action); }
        action.value = actionId;
        form.querySelector("button[type=submit],button:not([type])").textContent = "Save action";
      }
      if (acknowledgedAuthoredKey !== keyFor(form)) erase(acknowledgedAuthoredKey);
      setBaseline(form, frozen.authored);
      if (equal(formValues(form), frozen.authored)) erase(acknowledgedAuthoredKey); else mark(form);
      announce(payload?.message || success(frozen.operation)); await refresh(form, payload?.refresh || location.href);
    } catch { retainPending(form, frozen); form.dataset.pending = "true"; workspace().dataset.unresolved = "true"; announce("Save outcome unknown. Retry will use the exact original save; other saves are paused.", "notice error", true); }
    finally { workspace().dataset.inflight = ""; form.dataset.inflight = ""; form.removeAttribute("aria-busy"); form.querySelectorAll("button[type=submit],button:not([type])").forEach(button => { button.disabled = Boolean(form.querySelector("[data-unavailable-recovery]")); if (form.dataset.pending) button.textContent = "Retry save"; }); }
  }
  document.addEventListener("input", event => { const form = event.target.closest("form[data-editor]"); if (form) mark(form); const admin = event.target.closest("form[data-admin-form]"); if (admin) markAdmin(admin); });
  document.addEventListener("change", event => { const form = event.target.closest("form[data-editor]"); if (form) mark(form); const admin = event.target.closest("form[data-admin-form]"); if (admin) markAdmin(admin); });
  document.addEventListener("submit", event => { const form = event.target; if (form.matches("[data-workspace-form]")) { event.preventDefault(); submit(form, Boolean(form.dataset.pending)); return; } if (form.matches("[data-admin-form]")) form.dataset.dirty = "false"; if (form.matches("[data-guard-navigation]") && dirtyEditors().length) { event.preventDefault(); choice(form, "Leaving will discard unsaved workspace changes.", () => { discardDirtyRecovery(); form.submit(); }); } });
  document.addEventListener("click", event => { const cancel = event.target.closest("[data-cancel-editor]"); if (cancel) { const form = cancel.closest("form[data-editor]"); if (form?.dataset.dirty === "true") { event.preventDefault(); choice(cancel, `Discard unsaved changes in ${editorLabel(form)}?`, () => { discardToAuthoritative(form); form.querySelector("textarea,input,select")?.focus(); }); } return; } const link = event.target.closest("a[href]"); if (link && (dirtyEditors().length || dirtyAdminForms().length) && !link.dataset.cancelEditor) { event.preventDefault(); choice(link, "Leaving will discard unsaved changes.", () => { discardDirtyRecovery(); location.href = link.href; }); } });
  window.addEventListener("beforeunload", event => { if (dirtyEditors().length || dirtyAdminForms().length || workspace()?.dataset.unresolved === "true") { event.preventDefault(); event.returnValue = ""; } });
  document.querySelectorAll('form[action^="/admin"]:not([data-workspace-form])').forEach(form => { form.dataset.adminForm = "true"; form.dataset.baseline = JSON.stringify(formValues(form)); form.dataset.dirty = "false"; });
  clearForOtherUser(); initialize();
})();

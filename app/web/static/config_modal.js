/**
 * config_modal.js — MISRA Configure Rules Modal
 * Place in: app/web/static/config_modal.js
 * Include via <script> AFTER script.js in index.html
 *
 * Behaviour:
 *  - On load: each rule gets its MISRA category auto-selected (M→M, R→R, A→A)
 *  - "Apply Configuration" applies the current selections (defaults or overrides)
 *  - "Override Defaults" button becomes enabled only when user actually changes
 *    any chip away from the MISRA default — clicking it saves those overrides
 *  - A rule with NO chip selected is OMITTED (font fades, model skips it)
 */

(function () {
  "use strict";

  /* ── State ─────────────────────────────────────────────── */
  let _configToken = null;
  let _configRows = [];      // rows from /api/config/load
  let _hasOverride = false;   // true when user changed any chip from its default

  /* ── DOM refs ──────────────────────────────────────────── */
  const overlay = document.getElementById("config-modal-overlay");
  const closeBtn = document.getElementById("modal-close-btn");
  const openBtn = document.getElementById("config-open-btn");
  const configNote = document.getElementById("config-note");
  const configBody = document.getElementById("config-body");
  const applyBtn = document.getElementById("save-config-btn");
  const overrideBtn = document.getElementById("override-config-btn");
  const saveStatus = document.getElementById("config-status");
  const warningCard = document.getElementById("warning-card");
  const wnTitle = document.getElementById("wn-card-title");
  const wnBody = document.getElementById("wn-card-body");
  const wnCloseBtn = document.getElementById("wn-close-btn");

  /* ── Open / Close ──────────────────────────────────────── */
  function openModal() {
    overlay.classList.add("cm-active");
    document.body.style.overflow = "hidden";
    loadConfig();
  }

  function closeModal() {
    overlay.classList.remove("cm-active");
    document.body.style.overflow = "";
    hideWarningCard();
  }

  openBtn && openBtn.addEventListener("click", openModal);
  closeBtn && closeBtn.addEventListener("click", closeModal);

  overlay && overlay.addEventListener("click", function (e) {
    if (e.target === overlay) closeModal();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && overlay && overlay.classList.contains("cm-active")) closeModal();
  });

  /* ── Load config from server ───────────────────────────── */
  async function loadConfig() {
    if (!configNote || !configBody) return;
    configNote.textContent = "Loading configuration…";
    configBody.innerHTML = '<tr><td colspan="3" class="cm-loading-row"><div class="cm-spinner"></div> Loading rules…</td></tr>';
    if (saveStatus) { saveStatus.textContent = ""; saveStatus.className = "cm-save-status"; }
    _hasOverride = false;
    updateOverrideBtn();

    try {
      const res = await fetch("/api/config/load");
      const data = await res.json();

      if (data.error) {
        configNote.textContent = "⚠ " + data.error;
        configBody.innerHTML = `<tr><td colspan="3" class="cm-loading-row" style="color:#dc2626;">${data.error}</td></tr>`;
        return;
      }

      _configToken = data.token;
      _configRows = data.rows || [];

      configNote.textContent =
        `${data.count} rule(s) loaded — defaults set by MISRA category. ` +
        `Deselect a chip to omit a rule. Override and click Save Overrides to customise.`;

      renderTable(_configRows);
    } catch (err) {
      configNote.textContent = "⚠ Failed to load: " + err.message;
    }
  }

  /* ── Default chip for a row based on MISRA category ─────── */
  function defaultChip(row) {
    const cat = (row.misra_category || row.misra_category_display || "").toLowerCase();
    if (cat.includes("mandatory")) return "M";
    if (cat.includes("required")) return "R";
    if (cat.includes("advisory")) return "A";
    return "";
  }

  /* ── Render the rules table ─────────────────────────────── */
  function renderTable(rows) {
    configBody.innerHTML = "";

    if (!rows.length) {
      configBody.innerHTML = '<tr><td colspan="3" class="cm-loading-row">No rules found.</td></tr>';
      return;
    }

    rows.forEach(function (row) {
      const tr = document.createElement("tr");
      tr.dataset.rowIndex = row.row_index;

      /* Determine active chip: saved user_category if set, else MISRA default */
      const savedVal = (row.user_category || "").toUpperCase();
      const defVal = defaultChip(row);
      const activeVal = savedVal || defVal;   // use saved override, else MISRA default

      /* ── Col 1: Rule link ── */
      const tdRule = document.createElement("td");
      const link = document.createElement("a");
      link.className = "rule-link";
      link.textContent = row.rule_list || "—";
      link.href = "#";
      link.title = "Click to see Warning Message Nos.";
      link.addEventListener("click", function (e) { e.preventDefault(); showWarningCard(e, row); });
      tdRule.appendChild(link);

      /* ── Col 2: MISRA Category badge ── */
      const tdCat = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = "cm-cat-badge " + badgeClass(row.misra_category || "");
      badge.textContent = row.misra_category || "";
      tdCat.appendChild(badge);

      /* ── Col 3: M / R / A chips (radio-style, click to toggle off) ── */
      const tdSpec = document.createElement("td");
      const group = document.createElement("div");
      group.className = "cm-spec-group";

      ["M", "R", "A"].forEach(function (opt) {
        const label = document.createElement("label");
        label.className = "cm-spec-label";
        label.title = { M: "Mandatory", R: "Required", A: "Advisory" }[opt];

        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.name = "rule_spec_" + row.row_index;
        cb.value = opt;
        cb.checked = (activeVal === opt);
        cb.dataset.rowIndex = row.row_index;
        cb.dataset.opt = opt;
        cb.dataset.default = defVal;   // remember the MISRA default

        cb.addEventListener("change", function () {
          if (cb.checked) {
            /* Uncheck siblings */
            group.querySelectorAll('input[type="checkbox"]').forEach(function (s) {
              if (s !== cb) s.checked = false;
            });
          }
          /* Mark row as omitted if nothing selected */
          updateRowOmitted(tr, group);
          /* Check whether any chip differs from MISRA default */
          checkOverrideDirty();
        });

        const chip = document.createElement("span");
        chip.className = "cm-spec-chip chip-" + opt.toLowerCase();
        chip.textContent = opt;

        label.appendChild(cb);
        label.appendChild(chip);
        group.appendChild(label);
      });

      tdSpec.appendChild(group);
      tr.appendChild(tdRule);
      tr.appendChild(tdCat);
      tr.appendChild(tdSpec);
      configBody.appendChild(tr);

      /* Apply initial omit styling if nothing active */
      updateRowOmitted(tr, group);
    });
  }

  /* ── Omit styling: fade row when no chip selected ───────── */
  function updateRowOmitted(tr, group) {
    const anyChecked = !!group.querySelector('input[type="checkbox"]:checked');
    tr.classList.toggle("cm-row-omitted", !anyChecked);
  }

  /* ── Detect whether user overrode any MISRA default ────── */
  function checkOverrideDirty() {
    let dirty = false;
    configBody.querySelectorAll("tr[data-row-index]").forEach(function (tr) {
      const cbs = tr.querySelectorAll('input[type="checkbox"]');
      cbs.forEach(function (cb) {
        const defVal = cb.dataset.default || "";
        const isChecked = cb.checked;
        const isDefault = (cb.value === defVal);
        /* Dirty if: a non-default chip is selected, OR no chip is selected (omit) */
        if (isChecked && !isDefault) dirty = true;
        if (!isChecked) {
          const anyInRow = [...tr.querySelectorAll('input[type="checkbox"]')].some(c => c.checked);
          if (!anyInRow) dirty = true;
        }
      });
    });
    _hasOverride = dirty;
    updateOverrideBtn();
  }

  /* ── Override button state ──────────────────────────────── */
  function updateOverrideBtn() {
    if (!overrideBtn) return;
    overrideBtn.disabled = !_hasOverride;
    overrideBtn.title = _hasOverride
      ? "Save your custom overrides to the working copy"
      : "Override Defaults — change a chip first to enable this";
  }

  /* ── Collect current chip selections ────────────────────── */
  function collectUpdates() {
    const updates = [];
    configBody.querySelectorAll("tr[data-row-index]").forEach(function (tr, i) {
      const row = _configRows[i];
      if (!row) return;
      const checked = tr.querySelector('input[type="checkbox"]:checked');
      updates.push({
        row_index: row.row_index,
        user_category: checked ? checked.value : "",   // "" → server stores "-" (omitted)
      });
    });
    return updates;
  }

  /* ── Apply Configuration (always available) ─────────────── */
  applyBtn && applyBtn.addEventListener("click", async function () {
    if (!_configToken) {
      if (saveStatus) { saveStatus.textContent = "⚠ No config loaded."; saveStatus.className = "cm-save-status error"; }
      return;
    }
    if (saveStatus) { saveStatus.textContent = "Applying…"; saveStatus.className = "cm-save-status"; }
    applyBtn.disabled = true;

    try {
      const res = await fetch("/api/config/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: _configToken, updates: collectUpdates() }),
      });
      const data = await res.json();

      if (data.error) {
        if (saveStatus) { saveStatus.textContent = "⚠ " + data.error; saveStatus.className = "cm-save-status error"; }
        return;
      }
      if (data.rows) _configRows = data.rows;

      if (saveStatus) { saveStatus.textContent = "✓ Configuration applied!"; saveStatus.className = "cm-save-status"; }
      _hasOverride = false;
      updateOverrideBtn();
      setTimeout(closeModal, 1600);
    } catch (err) {
      if (saveStatus) { saveStatus.textContent = "⚠ " + err.message; saveStatus.className = "cm-save-status error"; }
    } finally {
      applyBtn.disabled = false;
    }
  });

  /* ── Save Overrides (only enabled when dirty) ───────────── */
  overrideBtn && overrideBtn.addEventListener("click", async function () {
    if (!_configToken || !_hasOverride) return;
    if (saveStatus) { saveStatus.textContent = "Saving overrides…"; saveStatus.className = "cm-save-status"; }
    overrideBtn.disabled = true;

    try {
      const res = await fetch("/api/config/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: _configToken, updates: collectUpdates() }),
      });
      const data = await res.json();

      if (data.error) {
        if (saveStatus) { saveStatus.textContent = "⚠ " + data.error; saveStatus.className = "cm-save-status error"; }
        return;
      }
      if (data.rows) _configRows = data.rows;

      if (saveStatus) { saveStatus.textContent = "✓ Overrides saved!"; saveStatus.className = "cm-save-status"; }
      _hasOverride = false;
      updateOverrideBtn();
      setTimeout(closeModal, 1600);
    } catch (err) {
      if (saveStatus) { saveStatus.textContent = "⚠ " + err.message; saveStatus.className = "cm-save-status error"; }
    } finally {
      overrideBtn.disabled = false;
    }
  });

  /* ── Badge CSS class helper ─────────────────────────────── */
  function badgeClass(cat) {
    const c = (cat || "").toLowerCase();
    if (c.includes("mandatory")) return "badge-mandatory";
    if (c.includes("required")) return "badge-required";
    if (c.includes("advisory")) return "badge-advisory";
    return "badge-other";
  }

  /* ── Warning Card (warning message nos.) ───────────────── */
  function showWarningCard(clickEvent, row) {
    if (!warningCard) return;
    const warnNos = (row.warning_message_nos || "").trim();
    if (wnTitle) wnTitle.textContent = "Rule " + row.rule_list + "  —  Warning Message Nos.";

    if (warnNos) {
      wnBody.textContent = warnNos;
      wnBody.className = "wn-card-body";
    } else {
      wnBody.textContent = "No warning message numbers available for this rule.";
      wnBody.className = "wn-card-body empty";
    }

    warningCard.style.display = "block";
    const rect = clickEvent.target.getBoundingClientRect();
    const cardW = 280;
    let left = rect.left;
    let top = rect.bottom + window.scrollY + 6;
    if (left + cardW > window.innerWidth - 16) left = window.innerWidth - cardW - 16;
    if (left < 8) left = 8;
    warningCard.style.left = left + "px";
    warningCard.style.top = top + "px";
  }

  function hideWarningCard() {
    if (warningCard) warningCard.style.display = "none";
  }

  wnCloseBtn && wnCloseBtn.addEventListener("click", hideWarningCard);

  document.addEventListener("click", function (e) {
    if (warningCard && warningCard.style.display === "block" &&
      !warningCard.contains(e.target) &&
      !e.target.classList.contains("rule-link")) {
      hideWarningCard();
    }
  });

})();
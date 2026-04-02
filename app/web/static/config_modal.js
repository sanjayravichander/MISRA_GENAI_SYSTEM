/**
 * config_modal.js — MISRA Configure Rules Modal
 * Place in: app/web/static/config_modal.js
 * Include via <script> AFTER script.js in index.html
 */

(function () {
  "use strict";

  /* ── State ─────────────────────────────────────────────── */
  let _configToken = null;
  let _configRows = [];     // rows as returned from /api/config/load

  /* ── DOM refs ──────────────────────────────────────────── */
  const overlay = document.getElementById("config-modal-overlay");
  const closeBtn = document.getElementById("modal-close-btn");
  const openBtn = document.getElementById("config-open-btn");
  const configNote = document.getElementById("config-note");
  const configBody = document.getElementById("config-body");
  const saveBtn = document.getElementById("save-config-btn");
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

  openBtn.addEventListener("click", openModal);
  closeBtn.addEventListener("click", closeModal);

  // Close when clicking the dark backdrop (outside the dialog)
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) closeModal();
  });

  // ESC key
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && overlay.classList.contains("cm-active")) closeModal();
  });

  /* ── Load config from server ───────────────────────────── */
  async function loadConfig() {
    configNote.textContent = "Loading configuration…";
    configBody.innerHTML =
      '<tr><td colspan="3" class="cm-loading-row"><div class="cm-spinner"></div> Loading rules…</td></tr>';
    saveStatus.textContent = "";
    saveStatus.className = "cm-save-status";

    try {
      const res = await fetch("/api/config/load");
      const data = await res.json();

      if (data.error) {
        configNote.textContent = "⚠ " + data.error;
        configBody.innerHTML =
          `<tr><td colspan="3" class="cm-loading-row" style="color:#dc2626;">${data.error}</td></tr>`;
        return;
      }

      _configToken = data.token;
      _configRows = data.rows || [];

      configNote.textContent =
        `${data.count} rule(s) loaded. Select M / R / A for each rule, then click Apply Configuration.`;

      renderTable(_configRows);
    } catch (err) {
      configNote.textContent = "⚠ Failed to load: " + err.message;
    }
  }

  /* ── Render the rules table ────────────────────────────── */
  function renderTable(rows) {
    configBody.innerHTML = "";

    if (!rows.length) {
      configBody.innerHTML =
        '<tr><td colspan="3" class="cm-loading-row">No rules found.</td></tr>';
      return;
    }

    rows.forEach(function (row) {
      const tr = document.createElement("tr");

      /* ── Col 1: Rule link ── */
      const tdRule = document.createElement("td");
      const link = document.createElement("a");
      link.className = "rule-link";
      link.textContent = row.rule_list || "—";
      link.href = "#";
      link.title = "Click to view Warning Message Nos. for Rule " + row.rule_list;
      link.addEventListener("click", function (e) {
        e.preventDefault();
        showWarningCard(e, row);
      });
      tdRule.appendChild(link);

      /* ── Col 2: MISRA Category badge ── */
      const tdCat = document.createElement("td");
      const catText = row.misra_category || row.misra_category_display || "";
      const badge = document.createElement("span");
      badge.className = "cm-cat-badge " + badgeClass(catText);
      badge.textContent = catText;
      tdCat.appendChild(badge);

      /* ── Col 3: M / R / A checkboxes (radio-style) ── */
      const tdSpec = document.createElement("td");
      const group = document.createElement("div");
      group.className = "cm-spec-group";

      const currentVal = (row.user_category || "").toUpperCase();

      ["M", "R", "A"].forEach(function (opt) {
        const label = document.createElement("label");
        label.className = "cm-spec-label";
        label.title = { M: "Mandatory", R: "Required", A: "Advisory" }[opt];

        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.name = "rule_spec_" + row.row_index;
        cb.value = opt;
        cb.checked = currentVal === opt;
        cb.dataset.rowIndex = row.row_index;
        cb.dataset.opt = opt;

        /* Enforce single-select: uncheck siblings when this is ticked */
        cb.addEventListener("change", function () {
          if (cb.checked) {
            group.querySelectorAll('input[type="checkbox"]').forEach(function (s) {
              if (s !== cb) s.checked = false;
            });
          }
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
    });
  }

  /* ── Badge CSS class helper ────────────────────────────── */
  function badgeClass(cat) {
    const c = (cat || "").toLowerCase();
    if (c.includes("mandatory")) return "badge-mandatory";
    if (c.includes("required")) return "badge-required";
    if (c.includes("advisory")) return "badge-advisory";
    return "badge-other";
  }

  /* ── Warning Card (shows warning message nos.) ─────────── */
  function showWarningCard(clickEvent, row) {
    const warnNos = (row.warning_message_nos || "").trim();
    wnTitle.textContent = "Rule " + row.rule_list + "  —  Warning Message Nos.";

    if (warnNos) {
      wnBody.textContent = warnNos;
      wnBody.className = "wn-card-body";
    } else {
      wnBody.textContent = "No warning message numbers available for this rule.";
      wnBody.className = "wn-card-body empty";
    }

    warningCard.style.display = "block";

    /* Position the card near the clicked link */
    const rect = clickEvent.target.getBoundingClientRect();
    const cardW = 280;
    let left = rect.left;
    let top = rect.bottom + window.scrollY + 6;

    // Keep card within viewport horizontally
    if (left + cardW > window.innerWidth - 16) {
      left = window.innerWidth - cardW - 16;
    }
    if (left < 8) left = 8;

    warningCard.style.left = left + "px";
    warningCard.style.top = top + "px";
  }

  function hideWarningCard() {
    warningCard.style.display = "none";
  }

  wnCloseBtn.addEventListener("click", hideWarningCard);

  // Hide warning card when clicking elsewhere
  document.addEventListener("click", function (e) {
    if (
      warningCard.style.display === "block" &&
      !warningCard.contains(e.target) &&
      !e.target.classList.contains("rule-link")
    ) {
      hideWarningCard();
    }
  });

  /* ── Apply / Save ──────────────────────────────────────── */
  saveBtn.addEventListener("click", async function () {
    if (!_configToken) {
      saveStatus.textContent = "⚠ No config loaded.";
      saveStatus.className = "cm-save-status error";
      return;
    }

    saveStatus.textContent = "Saving…";
    saveStatus.className = "cm-save-status";
    saveBtn.disabled = true;

    /* Collect updates from the rendered table rows */
    const updates = [];
    const tableRows = configBody.querySelectorAll("tr");

    tableRows.forEach(function (tr, i) {
      const row = _configRows[i];
      if (!row) return;

      const checked = tr.querySelector('input[type="checkbox"]:checked');
      updates.push({
        row_index: row.row_index,
        user_category: checked ? checked.value : "",   // "" → server stores "-"
      });
    });

    try {
      const res = await fetch("/api/config/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: _configToken, updates }),
      });
      const data = await res.json();

      if (data.error) {
        saveStatus.textContent = "⚠ " + data.error;
        saveStatus.className = "cm-save-status error";
        return;
      }

      /* Refresh local row state so re-renders stay in sync */
      if (data.rows) {
        _configRows = data.rows;
      }

      const savedFile = data.saved_file ? `  →  ${data.saved_file}` : "";
      saveStatus.textContent = "✓ Saved!" + savedFile;
      saveStatus.className = "cm-save-status";

      /* Auto-close modal after a moment */
      setTimeout(closeModal, 1600);
    } catch (err) {
      saveStatus.textContent = "⚠ Network error: " + err.message;
      saveStatus.className = "cm-save-status error";
    } finally {
      saveBtn.disabled = false;
    }
  });
})();
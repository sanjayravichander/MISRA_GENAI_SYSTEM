"use strict";
/* =========================================================
   SRM Technologies — MISRA Compliance Reviewer
   script.js  v6  (clean rewrite — fixed toggle listener scope)
   ========================================================= */

const IS_RESULTS = typeof window.MISRA_RUN_ID !== "undefined";
IS_RESULTS ? initResultsPage() : initIndexPage();

/* ============================================================
   INDEX PAGE
   ============================================================ */
function initIndexPage() {

  /* ── Element refs ── */
  const excelInput    = document.getElementById("excel-input");
  const cInput        = document.getElementById("c-input");
  const excelZone     = document.getElementById("excel-zone");
  const cZone         = document.getElementById("c-zone");
  const excelList     = document.getElementById("excel-list");
  const cList         = document.getElementById("c-list");
  const runBtn        = document.getElementById("run-btn");
  const fileSummary   = document.getElementById("file-summary");
  const uploadError   = document.getElementById("upload-error");
  const batchInput    = document.getElementById("batch-size");
  const batchMinus    = document.getElementById("batch-minus");
  const batchPlus     = document.getElementById("batch-plus");
  const configCard    = document.getElementById("config-card");
  const configToggleBtn = document.getElementById("config-toggle-btn");
  const configBody    = document.getElementById("config-body");
  const configNote    = document.getElementById("config-note");
  const configStatus  = document.getElementById("config-status");
  const saveConfigBtn = document.getElementById("save-config-btn");

  /* ── State ── */
  let excelFile    = null;
  let cFilesList   = [];
  let configToken  = null;
  let configRows   = [];
  let configLoaded = false;

  /* ── Init ── */
  setConfigExpanded(false);
  showConfigStatus("Loading rules from data folder…");
  autoLoadConfig();

  /* ── Batch stepper ── */
  batchMinus.addEventListener("click", () => {
    batchInput.value = Math.max(1, parseInt(batchInput.value, 10) - 1);
  });
  batchPlus.addEventListener("click", () => {
    batchInput.value = Math.min(15, parseInt(batchInput.value, 10) + 1);
  });

  /* ── Drop zones ── */
  [excelZone, cZone].forEach(zone => {
    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", e => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      const files = [...e.dataTransfer.files];
      zone === excelZone ? handleExcel(files[0]) : handleCFiles(files);
    });
    zone.addEventListener("click", e => {
      const inp = zone.querySelector("input[type=file]");
      if (inp && e.target !== inp) inp.click();
    });
  });

  /* ── File inputs ── */
  excelInput.addEventListener("change", async () => {
    await handleExcel(excelInput.files[0]);
  });                                                    // ← closed here

  cInput.addEventListener("change", () => handleCFiles([...cInput.files]));

  /* ── Config toggle ── THIS WAS PREVIOUSLY TRAPPED INSIDE excelInput handler ── */
  configToggleBtn.addEventListener("click", () => {
    if (!configLoaded) {
      showConfigStatus("Rules are still loading — please wait.", "err");
      return;
    }
    const nowOpen = !configCard.classList.contains("open");
    setConfigExpanded(nowOpen);
    configToggleBtn.textContent = nowOpen ? "▲ Close Configuration" : "Configure MISRA Rules";
  });

  /* ── Save config ── */
  saveConfigBtn.addEventListener("click", async () => {
    if (!configToken || !configLoaded) {
      showConfigStatus("No configuration loaded.", "err");
      return;
    }
    try {
      setConfigSaving(true);
      const updates = collectConfigSelections();
      const resp = await fetch("/api/config/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: configToken, updates }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Failed to save");
      configRows = data.rows || configRows;
      renderConfigTable(configRows);
      showConfigStatus("Configuration saved to Excel.", "ok");
    } catch (err) {
      showConfigStatus(err.message, "err");
    } finally {
      setConfigSaving(false);
      updateState();
    }
  });

  /* ── Run button ── */
  runBtn.addEventListener("click", async () => {
    if (!configToken || !cFilesList.length) return;

    uploadError.classList.add("hidden");
    runBtn.disabled = true;
    runBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
      </svg> Uploading…`;

    const fd = new FormData();
    fd.append("warning_report_token", configToken);
    cFilesList.forEach(f => fd.append("source_files", f));
    fd.append("batch_size", batchInput.value);

    const selectedCats = [...document.querySelectorAll('input[name="misra_category"]:checked')]
      .map(cb => cb.value);
    if (selectedCats.length) sessionStorage.setItem("misra_filter", selectedCats.join(","));
    else sessionStorage.removeItem("misra_filter");

    try {
      const resp = await fetch("/api/analyse", { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok) { showError(data.error || "Server error"); resetRunBtn(); return; }

      document.getElementById("progress-panel").classList.add("visible");
      const uploadCard = document.getElementById("upload-card");
      uploadCard.style.opacity = "0.35";
      uploadCard.style.pointerEvents = "none";
      uploadCard.style.transition = "opacity .3s ease";
      listenProgress(data.job_id, data.run_id);
    } catch (err) {
      showError("Connection error: " + err.message);
      resetRunBtn();
    }
  });

  /* ── Config body checkbox delegation ── */
  configBody.addEventListener("change", e => {
    const input = e.target;
    if (!input || !input.matches('input[type="checkbox"][data-spec]')) return;
    const row = input.closest("tr");
    if (!row) return;
    if (input.checked) {
      row.querySelectorAll('input[type="checkbox"][data-spec]').forEach(cb => {
        if (cb !== input) cb.checked = false;
      });
    }
    syncRowUI(row);
  });

  /* ================================================================
     FUNCTIONS
     ================================================================ */

  async function autoLoadConfig() {
    try {
      showConfigStatus("Loading rules…");
      const resp = await fetch("/api/config/load");
      const data = await resp.json();

      if (!resp.ok) throw new Error(data.error || "Server error loading config");

      configToken  = data.token || null;
      configRows   = data.rows  || [];
      configLoaded = configRows.length > 0;

      if (!configLoaded) {
        showConfigStatus("No rules found in the data folder.", "err");
        if (configNote) configNote.textContent = "No rules found. Check the data folder.";
        return;
      }

      renderConfigTable(configRows);

      if (configNote) {
        configNote.textContent =
          `${configRows.length} rule(s) loaded. ` +
          `Select M / R / A for each rule, then click Apply Configuration.`;
      }

      configToggleBtn.disabled = false;
      saveConfigBtn.disabled   = !configToken;
      setConfigExpanded(false);   // collapsed by default; user clicks to open
      showConfigStatus(`${configRows.length} rule(s) ready.`, "ok");

    } catch (err) {
      console.error("autoLoadConfig failed:", err);
      showConfigStatus("Could not load configuration: " + err.message, "err");
      if (configNote) configNote.textContent = "Failed to load rules. Check the server terminal.";
    }
  }

  async function handleExcel(file) {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["xlsx", "xls"].includes(ext)) { showError("Warning report must be .xlsx or .xls"); return; }
    excelFile = file;
    excelList.innerHTML = chipHTML(file.name);
    excelZone.classList.add("has-file");
    updateState();
  }

  function handleCFiles(files) {
    const valid = files.filter(f => /\.(c|h)$/i.test(f.name));
    if (!valid.length) { showError("No .c or .h files found"); return; }
    cFilesList = valid;
    cList.innerHTML = valid.map(f => chipHTML(f.name)).join("");
    cZone.classList.add("has-file");
    updateState();
  }

  function chipHTML(name) {
    return `<div class="file-chip"><span class="dot"></span>${escHtml(name)}</div>`;
  }

  function updateState() {
    const ready = !!configToken && cFilesList.length > 0;
    runBtn.disabled = !ready;
    if (ready) {
      const label = excelFile ? excelFile.name : "Config loaded";
      fileSummary.textContent =
        `${label} + ${cFilesList.length} source file${cFilesList.length > 1 ? "s" : ""}`;
      const batchRow = document.getElementById("batch-row");
      if (cFilesList.length === 1) {
        batchInput.value = 1;
        if (batchRow) batchRow.style.display = "none";
      } else {
        if (batchRow) batchRow.style.display = "";
      }
    }
  }

  function showError(msg) {
    uploadError.textContent = msg;
    uploadError.classList.remove("hidden");
    setTimeout(() => uploadError.classList.add("hidden"), 5000);
  }

  function showConfigStatus(msg, kind = "") {
    if (!configStatus) return;
    configStatus.textContent = msg || "";
    configStatus.className = "config-status" + (kind ? ` ${kind}` : "");
  }

  function setConfigSaving(isSaving) {
    saveConfigBtn.disabled = isSaving || !configLoaded;
    saveConfigBtn.textContent = isSaving ? "Saving…" : "Apply Configuration";
  }

  function setConfigExpanded(expanded) {
    configCard.classList.toggle("open", expanded);
  }

  function renderConfigEmpty() {
    if (!configBody) return;
    configBody.innerHTML = `<tr class="config-empty-row"><td colspan="3">No rules loaded.</td></tr>`;
    saveConfigBtn.disabled = true;
  }

  function renderConfigTable(rows) {
    if (!configBody) return;
    if (!rows || !rows.length) { renderConfigEmpty(); return; }

    configBody.innerHTML = rows.map(row => {
      const selected = normalizeUserCategory(row.user_category || "");
      return `
        <tr data-row-index="${row.row_index}">
          <td>${escHtml(row.rule_list || "")}</td>
          <td>${escHtml(displayMisraCategory(row.misra_category || ""))}</td>
          <td>
            <div class="user-spec-group">
              ${userSpecOptionHTML("M", selected === "M")}
              ${userSpecOptionHTML("R", selected === "R")}
              ${userSpecOptionHTML("A", selected === "A")}
            </div>
          </td>
        </tr>`;
    }).join("");

    saveConfigBtn.disabled = !configLoaded;
  }

  function displayMisraCategory(value) {
    const raw   = String(value || "").trim();
    const upper = raw.toUpperCase();
    if (upper === "MISRA-M" || upper === "MANDATORY") return "Mandatory";
    if (upper === "MISRA-R" || upper === "REQUIRED")  return "Required";
    if (upper === "MISRA-A" || upper === "ADVISORY")  return "Advisory";
    return raw;
  }

  function userSpecOptionHTML(value, active) {
    return `
      <label class="user-spec-option ${active ? "active" : ""}">
        <input type="checkbox" data-spec="${value}" ${active ? "checked" : ""} />
        <span class="user-spec-badge ${active ? "active" : ""}">${value}</span>
      </label>`;
  }

  function syncRowUI(row) {
    const checked = row.querySelector('input[type="checkbox"][data-spec]:checked');
    row.querySelectorAll(".user-spec-option").forEach(opt => opt.classList.remove("active"));
    row.querySelectorAll(".user-spec-badge").forEach(b => b.classList.remove("active"));
    if (checked) {
      const label = checked.closest(".user-spec-option");
      if (label) {
        label.classList.add("active");
        const badge = label.querySelector(".user-spec-badge");
        if (badge) badge.classList.add("active");
      }
    }
  }

  function collectConfigSelections() {
    const updates = [];
    document.querySelectorAll("#config-body tr[data-row-index]").forEach(row => {
      const rowIndex = parseInt(row.dataset.rowIndex, 10);
      const checked  = row.querySelector('input[type="checkbox"][data-spec]:checked');
      updates.push({ row_index: rowIndex, user_category: checked ? checked.dataset.spec : "" });
    });
    return updates;
  }

  function normalizeUserCategory(value) {
    const raw = String(value || "").trim().toUpperCase();
    if (!raw) return "";
    if (["M", "R", "A"].includes(raw)) return raw;
    if (raw.includes("M")) return "M";
    if (raw.includes("R")) return "R";
    if (raw.includes("A")) return "A";
    return "";
  }

  function resetRunBtn() {
    runBtn.disabled = false;
    runBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </svg> Start Review`;
  }

  /* ── SSE progress stepper ── */
  const PHASE_MAP = { "6a": "ph-6a", "6b": "ph-6b", "7": "ph-7", "8": "ph-8" };

  function listenProgress(jobId, runId) {
    const fill     = document.getElementById("progress-fill");
    const pctLabel = document.getElementById("progress-pct");
    const statusLn = document.getElementById("status-line");
    const stWrap   = document.getElementById("stream-table-wrap");
    const stTbody  = document.getElementById("stream-tbody");
    const streamRows = {};

    const es = new EventSource(`/api/progress/${jobId}`);

    es.onmessage = evt => {
      let msg; try { msg = JSON.parse(evt.data); } catch { return; }
      if (msg.type === "heartbeat") return;

      let pct = null;
      if (typeof msg.progress === "number") {
        pct = msg.progress;
      } else if (msg.type === "warning_start" && typeof msg.pct === "number") {
        const base  = msg.phase === "8" ? 80 : 40;
        const range = msg.phase === "8" ? 19 : 40;
        pct = Math.round(base + (msg.pct / 100) * range);
      } else if (msg.type === "phase_start") {
        pct = ({ "6a": 5, "6b": 20, "7": 40, "8": 80 })[msg.phase] ?? null;
      } else if (msg.type === "phase_done") {
        pct = ({ "6a": 20, "6b": 40, "7": 80, "8": 99 })[msg.phase] ?? null;
      }
      if (pct !== null) {
        fill.style.width = pct + "%";
        if (pctLabel) pctLabel.textContent = pct + "%";
      }

      if (msg.label) statusLn.textContent = plainEnglish(msg.label, msg.detail);
      else if (msg.type === "warning_start" && msg.detail) statusLn.textContent = plainDetail(msg.detail);
      else if (msg.type === "detail"         && msg.detail) statusLn.textContent = plainDetail(msg.detail);

      if (msg.phase && PHASE_MAP[msg.phase]) {
        const phEl = document.getElementById(PHASE_MAP[msg.phase]);
        if (phEl) {
          if (msg.type === "phase_start") {
            document.querySelectorAll(".phase-item").forEach(el => el.classList.remove("active"));
            phEl.classList.add("active");
            phEl.querySelector(".phase-detail").textContent = plainDetail(msg.detail);
          } else if (msg.type === "phase_done") {
            phEl.classList.remove("active"); phEl.classList.add("done");
            phEl.querySelector(".phase-badge").textContent = "✓";
            phEl.querySelector(".phase-detail").textContent = plainDetail(msg.detail);
          } else if (msg.type === "warning_done") {
            phEl.querySelector(".phase-detail").textContent = plainDetail(msg.detail);
          }
        }
      }

      if (msg.warning_id && (msg.phase === "7" || msg.phase === "8")) {
        stWrap.classList.remove("hidden");
        const wid       = msg.warning_id;
        const stepLabel = msg.phase === "7" ? "Creating fix" : "Checking fix quality";

        if (msg.type === "warning_start") {
          if (!streamRows[wid]) {
            const tr = document.createElement("tr");
            tr.id = "srow-" + wid;
            tr.innerHTML = `
              <td>${escHtml(wid)}</td><td>—</td><td>—</td>
              <td>${escHtml(stepLabel)}</td>
              <td><span class="st-badge running">In progress</span></td>`;
            stTbody.prepend(tr);
            streamRows[wid] = tr;
            tr.classList.add("stream-new");
            setTimeout(() => tr.classList.remove("stream-new"), 900);
          } else {
            streamRows[wid].cells[3].textContent = stepLabel;
            streamRows[wid].cells[4].innerHTML = `<span class="st-badge running">In progress</span>`;
          }
        } else if (msg.type === "warning_done") {
          const tr = streamRows[wid];
          if (tr) {
            tr.cells[3].textContent = stepLabel;
            tr.cells[4].innerHTML = `<span class="st-badge done">Done</span>`;
          }
        }
      }

      if (msg.type === "done") {
        es.close();
        const targetId = msg.run_id || runId || jobId;
        document.querySelectorAll(".phase-item").forEach(el => {
          el.classList.remove("active"); el.classList.add("done");
          el.querySelector(".phase-badge").textContent = "✓";
        });
        const doneEl = document.getElementById("ph-done");
        if (doneEl) {
          doneEl.classList.add("done");
          doneEl.querySelector(".phase-badge").textContent = "✓";
          doneEl.querySelector(".phase-detail").textContent = "Open your report";
        }
        if (pctLabel) pctLabel.textContent = "100%";
        statusLn.textContent = "All done — loading your report…";
        setTimeout(() => { window.location.href = `/results/${targetId}`; }, 1400);
      }

      if (msg.type === "error") {
        es.close();
        document.querySelectorAll(".phase-item.active").forEach(el => {
          el.classList.remove("active"); el.classList.add("error");
        });
        statusLn.textContent = "Something went wrong. Please try again.";
        const ep = document.createElement("div");
        ep.className = "error-panel mt-16";
        ep.textContent = msg.message || msg.detail || "Unknown error";
        document.getElementById("progress-panel").appendChild(ep);
        const uploadCard = document.getElementById("upload-card");
        uploadCard.style.opacity = "1";
        uploadCard.style.pointerEvents = "auto";
        resetRunBtn();
      }
    };

    es.onerror = () => {
      es.close();
      statusLn.textContent = "Connection lost — please check and try again.";
    };
  }

  function plainEnglish(label, detail) {
    const REPLACEMENTS = [
      [/phase\s*6a/gi, "Step 1"], [/phase\s*6b/gi, "Step 2"],
      [/phase\s*7/gi,  "Step 3"], [/phase\s*8/gi,  "Step 4"],
      [/parsing/gi, "Reading"],
      [/qdrant|faiss|bge|embedding/gi, "rule lookup"],
      [/llm|llama|mistral|model/gi,    "AI engine"],
      [/orchestrat\w*/gi,              "pipeline"],
      [/misra_context|kb_chunks?/gi,   "rule details"],
    ];
    let s = label + (detail ? " — " + detail : "");
    REPLACEMENTS.forEach(([rx, rep]) => { s = s.replace(rx, rep); });
    return s;
  }

  function plainDetail(detail) {
    if (!detail) return "";
    return detail
      .replace(/qdrant|faiss|bge|embedding/gi, "rule lookup")
      .replace(/llm|llama|mistral/gi, "AI engine")
      .replace(/parsed_warnings?/gi,  "warnings read");
  }

} // ← end initIndexPage


/* ============================================================
   RESULTS PAGE
   ============================================================ */
function initResultsPage() {
  const root  = document.getElementById("results-root");
  const runId = window.MISRA_RUN_ID;
  let allWarnings = [];

  loadResult();

  async function loadResult() {
    try {
      const r    = await fetch(`/api/result/${runId}`);
      const data = await r.json();
      if (!r.ok || data.error) {
        root.innerHTML = `<div class="error-panel">${escHtml(data.error || "Failed to load results")}</div>`;
        return;
      }
      allWarnings = data.warnings || [];
      root.innerHTML = buildShell(data);

      if (allWarnings.length === 0) {
        const noteMsg = data.misra_filter_note ||
          "No warnings were found. Try selecting Advisory, Required, or Mandatory on the upload page.";
        document.getElementById("warning-list").innerHTML = `
          <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:40px;margin-bottom:16px;">ℹ️</div>
            <div style="font-size:18px;font-weight:700;color:var(--text);margin-bottom:10px;">No warnings to show</div>
            <div style="font-size:14px;color:var(--text-sub);max-width:480px;margin:0 auto;">${escHtml(noteMsg)}</div>
            <a href="/" style="display:inline-block;margin-top:24px;" class="btn btn-primary">← Try a different selection</a>
          </div>`;
        attachFilterHandlers();
        return;
      }

      renderWarnings(allWarnings);
      attachFilterHandlers();
    } catch (err) {
      root.innerHTML = `<div class="error-panel">Failed to load: ${escHtml(err.message)}</div>`;
    }
  }

  function buildShell(data) {
    const s     = data.summary || {};
    const total = s.total ?? (data.warnings || []).length;
    return `
    <div style="padding:40px 0 28px;border-bottom:1px solid var(--border);margin-bottom:32px;">
      <div class="hero-eyebrow" style="margin-bottom:16px;">
        <span class="hero-eyebrow-dot"></span>Run ${escHtml(data.run_id)}
      </div>
      <h1 style="font-size:clamp(22px,3vw,34px);font-weight:800;letter-spacing:-.03em;margin-bottom:10px;">Review Report</h1>
      <p style="color:var(--text-sub);font-size:14px;">${total} warning${total !== 1 ? "s" : ""} reviewed</p>
    </div>
    <div class="stat-grid">
      <div class="stat-tile s-total"><div class="stat-number">${total}</div><div class="stat-label">Total</div></div>
      <div class="stat-tile s-high"><div class="stat-number">${s.high ?? "—"}</div><div class="stat-label">High Confidence</div></div>
      <div class="stat-tile s-medium"><div class="stat-number">${s.medium ?? "—"}</div><div class="stat-label">Medium Confidence</div></div>
      <div class="stat-tile s-low"><div class="stat-number">${s.low ?? "—"}</div><div class="stat-label">Low Confidence</div></div>
      <div class="stat-tile s-review"><div class="stat-number">${s.manual ?? "—"}</div><div class="stat-label">Needs Review</div></div>
    </div>
    <div class="filter-row" id="filter-bar">
      <span class="filter-label-text">Show</span>
      <button class="filter-btn active" data-filter="all">All</button>
      <button class="filter-btn" data-filter="high">High Confidence</button>
      <button class="filter-btn" data-filter="medium">Medium Confidence</button>
      <button class="filter-btn" data-filter="low">Low Confidence</button>
      <button class="filter-btn" data-filter="review">Needs Review</button>
      <span class="filter-label-text" style="margin-left:8px;">Rule type</span>
      <button class="filter-btn" data-misra="advisory">Advisory</button>
      <button class="filter-btn" data-misra="required">Required</button>
      <button class="filter-btn" data-misra="mandatory">Mandatory</button>
    </div>
    <div id="misra-no-results" class="misra-no-results hidden">
      <div class="misra-no-results-icon">ℹ️</div>
      <div>
        <div class="misra-no-results-title">No warnings match this rule type</div>
        <div class="misra-no-results-body" id="misra-no-results-body">
          None of the warnings in this report belong to the selected category.
        </div>
      </div>
    </div>
    <div class="warning-list" id="warning-list"></div>`;
  }

  function renderWarnings(ws) {
    const list = document.getElementById("warning-list");
    if (!list) return;
    list.innerHTML = ws.map((w, i) => buildWarningCard(w, i)).join("");
  }

  function attachFilterHandlers() {
    let activeConf  = "all";
    let activeMisra = null;

    function applyFilters() {
      const cards = document.querySelectorAll(".warning-card");
      let visible = 0;
      cards.forEach(card => {
        const confOk  = activeConf === "all"
          || (activeConf === "review" && card.dataset.review === "true")
          || card.dataset.conf === activeConf;
        const misraOk = !activeMisra || card.dataset.misra === activeMisra;
        const show    = confOk && misraOk;
        card.style.display = show ? "" : "none";
        if (show) visible++;
      });
      const noRes = document.getElementById("misra-no-results");
      if (noRes) {
        if (visible === 0 && activeMisra) {
          noRes.classList.remove("hidden");
          const body = document.getElementById("misra-no-results-body");
          if (body) {
            const label = activeMisra.charAt(0).toUpperCase() + activeMisra.slice(1);
            body.textContent = `None of the warnings are categorised as "${label}". Choose "All" to see every warning.`;
          }
        } else {
          noRes.classList.add("hidden");
        }
      }
    }

    document.querySelectorAll(".filter-btn[data-filter]").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn[data-filter]").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeConf = btn.dataset.filter;
        applyFilters();
      });
    });

    document.querySelectorAll(".filter-btn[data-misra]").forEach(btn => {
      btn.addEventListener("click", () => {
        if (btn.classList.contains("active")) {
          btn.classList.remove("active");
          activeMisra = null;
        } else {
          document.querySelectorAll(".filter-btn[data-misra]").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          activeMisra = btn.dataset.misra;
        }
        applyFilters();
      });
    });

    const savedFilter = sessionStorage.getItem("misra_filter");
    if (savedFilter) {
      sessionStorage.removeItem("misra_filter");
      const cats = savedFilter.split(",").map(s => s.trim()).filter(Boolean);
      if (cats.length === 1) {
        const btn = document.querySelector(`.filter-btn[data-misra="${cats[0]}"]`);
        if (btn) { btn.classList.add("active"); activeMisra = cats[0]; applyFilters(); }
      }
    }
  }
} // ← end initResultsPage


/* ============================================================
   BUILD WARNING CARD
   ============================================================ */
function buildWarningCard(w, idx) {
  const ev        = w.evaluation || w.evaluator_result || {};
  const conf      = (ev.overall_confidence || w.confidence || "").toLowerCase();
  const isReview  = !!(ev.manual_review_required || ev.flag_for_review || ev.needs_manual_review);
  const wId       = w.warning_id || `W${idx + 1}`;
  const ruleId    = w.rule_id || w.misra_rule || "";
  const msg       = w.message || w.warning_message || "";
  const loc       = w.file_path ? baseName(w.file_path) : "";
  const sev       = (w.severity || "").toLowerCase();
  const confClass = isReview ? "review" : (conf || "high");
  const confLabel = isReview ? "Needs Review" : (conf ? conf.charAt(0).toUpperCase() + conf.slice(1) : "—");
  const misraCat  = deriveMisraCategory(w);

  return `
  <div class="warning-card ${isReview ? "review-flag" : ""}"
       data-conf="${escHtml(conf)}" data-review="${isReview}"
       data-id="${escHtml(wId)}" data-misra="${escHtml(misraCat)}"
       style="animation-delay:${Math.min(idx * 0.035, 0.5)}s">
    <div class="warning-header" onclick="toggleCard('${escHtml(wId)}')">
      <span class="w-id">${escHtml(wId)}</span>
      ${ruleId ? `<span class="w-rule-pill">Rule ${escHtml(formatRuleId(ruleId))}</span>` : ""}
      ${sev    ? `<span class="w-sev-badge ${escHtml(sev)}">${escHtml(w.severity || sev)}</span>` : ""}
      <span class="w-msg">${escHtml(msg)}</span>
      ${loc    ? `<span class="w-loc">${escHtml(loc)}</span>` : ""}
      <span class="conf-badge ${confClass}">${confLabel}</span>
      <svg class="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </div>
    <div class="warning-detail">
      ${buildWarningDetail(w, ev, isReview, wId)}
    </div>
  </div>`;
}

function deriveMisraCategory(w) {
  const rt = (w.rule_type || "").toLowerCase();
  if (rt === "mandatory") return "mandatory";
  if (rt === "required")  return "required";
  if (rt === "advisory")  return "advisory";
  const cat = (w.rule_category || w.misra_category || "").toLowerCase();
  if (cat.includes("mandatory")) return "mandatory";
  if (cat.includes("required"))  return "required";
  if (cat.includes("advisory"))  return "advisory";
  const ctx = w.misra_context || w.retrieved_context || [];
  if (Array.isArray(ctx)) {
    for (const chunk of ctx) {
      const g = (chunk.guidelines || chunk.description || "").toLowerCase();
      if (g.includes("(mandatory)")) return "mandatory";
      if (g.includes("(required)"))  return "required";
      if (g.includes("(advisory)"))  return "advisory";
    }
  }
  return "";
}

function buildWarningDetail(w, ev, isReview, wId) {
  let html = "";

  if (isReview) {
    html += `<div class="review-banner mt-16">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      Flagged for manual review — we recommend a developer checks this one.
    </div>`;
  }

  const SKIP_KEYS = new Set([
    "source_context","source_lines","misra_context","retrieved_context",
    "line_start","line_end","_excel_row","_source_context","_from_cache",
    "evaluation","evaluator_result","ranked_fixes","fix_suggestions","fixes",
  ]);
  const row     = w._excel_row || {};
  const rowKeys = Object.keys(row).filter(k => !SKIP_KEYS.has(k) && row[k] && String(row[k]).trim());
  if (rowKeys.length) {
    html += `<div class="detail-section">
      <div class="detail-section-title">Warning Details</div>
      <table class="excel-table">
        ${rowKeys.map(k => `<tr><td>${escHtml(friendlyKey(k))}</td><td>${escHtml(String(row[k]))}</td></tr>`).join("")}
      </table>
    </div>`;
  }

  const srcCtxRaw = w._source_context || w.source_context || w.source_code || "";
  let sourceCode  = "";
  let flaggedLines = new Set();

  if (typeof srcCtxRaw === "string") {
    sourceCode = srcCtxRaw;
  } else if (Array.isArray(srcCtxRaw)) {
    sourceCode = srcCtxRaw.join("\n");
  } else if (srcCtxRaw && typeof srcCtxRaw === "object") {
    if (srcCtxRaw.context_text) {
      sourceCode = srcCtxRaw.context_text;
      if (Array.isArray(srcCtxRaw.flagged_lines) && srcCtxRaw.flagged_lines.length)
        flaggedLines = new Set(srcCtxRaw.flagged_lines.map(Number));
    } else {
      sourceCode = srcCtxRaw.code || srcCtxRaw.text || srcCtxRaw.content || srcCtxRaw.source || JSON.stringify(srcCtxRaw, null, 2);
    }
  }

  if (sourceCode) {
    const parsedLines = sourceCode.split("\n").map(ln => {
      const hasArrow = ln.includes(">>>");
      const clean    = ln.replace(/^\s*>>>/, "   ");
      const m        = clean.match(/^\s*(\d+)\s+(.*)/);
      if (!m) return null;
      const num  = m[1];
      const code = m[2].trimEnd();
      if (code.trim() === "") return null;
      const lineNum = parseInt(num, 10);
      const flagged = flaggedLines.size > 0 ? flaggedLines.has(lineNum) : hasArrow;
      return { num, code, flagged };
    }).filter(Boolean);

    if (parsedLines.length) {
      const firstFlaggedIdx = parsedLines.findIndex(l => l.flagged);
      const lineHtml = parsedLines.map(({ num, code, flagged }, idx) =>
        `<div class="${flagged ? "code-row hl" : "code-row"}"${idx === firstFlaggedIdx ? ` id="flagged-${escHtml(wId)}"` : ""}>` +
        `<span class="ln-num">${escHtml(num)}</span><span class="ln-code">${escHtml(code)}</span></div>`
      ).join("");
      html += `<div class="detail-section">
        <div class="detail-section-title" style="display:flex;align-items:center;gap:10px;">
          Flagged Code<span class="flagged-badge">⚠ violated line highlighted</span>
        </div>
        <div class="source-block" id="src-${escHtml(wId)}">${lineHtml}</div>
      </div>`;
    }
  }

  function toText(val) {
    if (!val) return "";
    if (typeof val === "string") return val.trim();
    if (Array.isArray(val)) return val.join(", ");
    if (typeof val === "object") {
      const best = val.summary || val.why || val.text || val.description || val.content || val.message || val.detail;
      if (best) return String(best).trim();
      return Object.entries(val).filter(([k,v]) => typeof v === "string" && v.length > 3).map(([,v]) => v).join(" ") || JSON.stringify(val);
    }
    return String(val);
  }

  const explText = toText(w.explanation || ev.explanation || "");
  if (explText) html += `<div class="detail-section"><div class="detail-section-title">What's wrong</div><div class="info-box">${escHtml(explText)}</div></div>`;

  const riskText = toText(w.risk_analysis || ev.risk_analysis || "");
  if (riskText) html += `<div class="detail-section"><div class="detail-section-title">Why it matters</div><div class="info-box">${escHtml(riskText)}</div></div>`;

  const ruleText = getRuleText(w);
  if (ruleText) html += `<div class="detail-section"><div class="detail-section-title">Rule ${escHtml(formatRuleId(w.rule_id || ""))}</div><div class="info-box">${escHtml(ruleText)}</div></div>`;

  const fixes = w.ranked_fixes || w.fix_suggestions || w.fixes || [];
  if (fixes.length) {
    const beforeCode = sourceCode || "[source code not available]";
    const firstFix   = fixes[0];
    const afterCode  = extractAfterCode(firstFix);

    function renderCodeBlock(raw) {
      if (!raw || raw === "[source code not available]")
        return `<div class="code-row"><span class="ln-num"> </span><span class="ln-code">[source code not available]</span></div>`;
      const rows = raw.split("\n").map(ln => {
        const isFlagged = ln.trimStart().startsWith(">>>");
        const clean = ln.replace(/^(\s*>>>)/, "   ");
        const m = clean.match(/^\s*(\d+)\s*(.*)/);
        if (!m) { const code = ln.trimEnd(); return code ? `<div class="code-row"><span class="ln-num"></span><span class="ln-code">${escHtml(code)}</span></div>` : null; }
        const num = m[1]; const code = m[2].trimEnd();
        if (!code.trim()) return null;
        const cls = (isFlagged || ln.includes(">>>")) ? ' class="code-row hl"' : ' class="code-row"';
        return `<div${cls}><span class="ln-num">${escHtml(num)}</span><span class="ln-code">${escHtml(code)}</span></div>`;
      }).filter(Boolean);
      return rows.length ? rows.join("") : `<div class="code-row"><span class="ln-num"> </span><span class="ln-code">${escHtml(raw)}</span></div>`;
    }

    html += `<div class="detail-section">
      <div class="detail-section-title">Suggested Fix</div>
      <div class="fix-area">
        <div class="fix-panel-wrap">
          <div class="fix-panel-label">Before (current code)</div>
          <div class="code-diff-panel before"><div class="code-diff-label">Before</div>${renderCodeBlock(beforeCode)}</div>
        </div>
        <div class="fix-panel-wrap">
          <div class="fix-panel-label">
            After (fix applied)
            ${fixes.length > 1 ? `<button class="fix-selector-btn" onclick="openFixPopover('${escHtml(wId)}')" id="fix-btn-${escHtml(wId)}">Choose fix ▾ (${fixes.length} options)</button>` : ""}
          </div>
          <div class="code-diff-panel after" id="after-block-${escHtml(wId)}">
            <div class="code-diff-label">After${fixes.length > 1 ? `<span id="fix-active-label-${escHtml(wId)}" style="margin-left:8px;font-size:10px;color:var(--text-muted);">Fix 1 selected</span>` : ""}</div>
            <div id="after-code-${escHtml(wId)}">${renderAfterCode(afterCode)}</div>
          </div>
        </div>
      </div>`;

    const evalNotes = ev.evaluator_notes || ev.notes || ev.summary || "";
    if (evalNotes) html += `<div class="info-box eval-note" style="margin-top:12px;">${escHtml(evalNotes)}</div>`;
    html += `</div>`;

    window._fixData = window._fixData || {};
    window._fixData[wId] = { fixes, beforeCode };
  }

  const devRaw = w.deviation_advice || ev.deviation_advice || "";
  if (devRaw) {
    let devHtml = "";
    if (typeof devRaw === "object") {
      const labelMap = { deviation_possible:"Deviation possible", recommended_decision:"Recommended action", required_justification:"Justification required", review_notes:"Review notes" };
      devHtml = Object.entries(devRaw).filter(([,v]) => v && String(v).trim())
        .map(([k,v]) => `<div style="margin-bottom:6px;"><span style="font-weight:600;color:var(--text);">${escHtml(labelMap[k]||k.replace(/_/g," "))}:</span><span style="color:var(--text-sub);"> ${escHtml(String(v))}</span></div>`)
        .join("");
    } else {
      devHtml = escHtml(String(devRaw));
    }
    if (devHtml) html += `<div class="detail-section"><div class="detail-section-title">Exception / Deviation Note</div><div class="info-box deviation">${devHtml}</div></div>`;
  }

  return html || `<div class="text-muted mt-16" style="font-size:12px;">No details available.</div>`;
}

function renderAfterCode(raw) {
  if (!raw) return "";
  return raw.split("\n").map(ln => {
    const m = ln.match(/^\s*(\d+)\s*(.*)/);
    if (!m) { const code = ln.trimEnd(); return code ? `<div class="code-row"><span class="ln-num"></span><span class="ln-code">${escHtml(code)}</span></div>` : null; }
    const num = m[1]; const code = m[2].trimEnd();
    if (!code.trim()) return `<div class="code-row" style="min-height:4px;padding:0;"><span class="ln-num" style="opacity:.3;">${escHtml(num)}</span><span class="ln-code"></span></div>`;
    return `<div class="code-row"><span class="ln-num">${escHtml(num)}</span><span class="ln-code">${escHtml(code)}</span></div>`;
  }).filter(Boolean).join("");
}

function extractAfterCode(fix) {
  if (!fix) return "";
  const codeRaw = fix.patched_code || fix.corrected_code || fix.code_change || fix.fixed_code || fix.code || "";
  let code = typeof codeRaw === "string" ? codeRaw
    : Array.isArray(codeRaw) ? codeRaw.join("\n")
    : codeRaw ? (codeRaw.AFTER || codeRaw.after || codeRaw.code || JSON.stringify(codeRaw, null, 2))
    : "";
  const afIdx = code.toUpperCase().indexOf("AFTER:");
  if (afIdx !== -1) {
    code = code.slice(afIdx + 6).trim().replace(/^(MISRA Rules Applied|Rationale|Risk Level|Confidence|Note)[^\n]*\n?/gim, "").trim();
  } else {
    const beIdx = code.toUpperCase().indexOf("BEFORE:");
    if (beIdx !== -1) {
      const aftIdx2 = code.toUpperCase().indexOf("AFTER:", beIdx);
      code = aftIdx2 !== -1 ? code.slice(aftIdx2 + 6).trim() : code.slice(beIdx + 7).trim();
    }
  }
  return code || "[fix code not available]";
}


/* ============================================================
   FIX POPOVER
   ============================================================ */
window.openFixPopover = function (wId) {
  const data = (window._fixData || {})[wId];
  if (!data) return;
  const { fixes } = data;
  const overlay = document.createElement("div");
  overlay.className = "fix-popover-overlay";
  overlay.id = "fix-overlay-" + wId;
  const optionsHtml = fixes.map((f, i) => {
    const conf  = (f.confidence || "").toLowerCase();
    const title = f.fix_title || f.title || f.description || `Fix ${i + 1}`;
    const rat   = f.rationale || "";
    return `<div class="fix-option ${i === 0 ? "selected" : ""}" data-idx="${i}" onclick="selectFixOption(this,'${escHtml(wId)}')">
      <div class="fix-option-header">
        <span class="fix-option-rank">Fix ${i + 1}</span>
        <span class="fix-option-title">${escHtml(title)}</span>
        ${conf ? `<span class="fix-option-conf ${conf}">${conf.charAt(0).toUpperCase() + conf.slice(1)}</span>` : ""}
      </div>
      ${rat ? `<div class="fix-option-rationale">${escHtml(rat)}</div>` : ""}
    </div>`;
  }).join("");
  overlay.innerHTML = `<div class="fix-popover">
    <div class="fix-popover-title">Choose a Fix</div>
    <div class="fix-popover-sub">Select which fix suggestion to show in the "After" panel.</div>
    ${optionsHtml}
    <div class="fix-popover-actions">
      <button class="btn btn-ghost btn-sm" onclick="closeFixPopover('${escHtml(wId)}')">Cancel</button>
      <button class="btn btn-primary btn-sm" onclick="applyFixChoice('${escHtml(wId)}')">Apply</button>
    </div>
  </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", e => { if (e.target === overlay) closeFixPopover(wId); });
};

window.selectFixOption = function (el, wId) {
  const overlay = document.getElementById("fix-overlay-" + wId);
  if (!overlay) return;
  overlay.querySelectorAll(".fix-option").forEach(o => o.classList.remove("selected"));
  el.classList.add("selected");
};

window.closeFixPopover = function (wId) {
  const overlay = document.getElementById("fix-overlay-" + wId);
  if (overlay) overlay.remove();
};

window.applyFixChoice = function (wId) {
  const overlay  = document.getElementById("fix-overlay-" + wId);
  if (!overlay) return;
  const selected = overlay.querySelector(".fix-option.selected");
  if (!selected) { closeFixPopover(wId); return; }
  const idx    = parseInt(selected.dataset.idx);
  const data   = (window._fixData || {})[wId];
  if (!data) { closeFixPopover(wId); return; }
  const newCode  = extractAfterCode(data.fixes[idx]);
  const codeEl   = document.getElementById("after-code-" + wId);
  const labelEl  = document.getElementById("fix-active-label-" + wId);
  if (codeEl)  codeEl.innerHTML   = renderAfterCode(newCode);
  if (labelEl) labelEl.textContent = `Fix ${idx + 1} selected`;
  closeFixPopover(wId);
};


/* ============================================================
   SHARED HELPERS
   ============================================================ */
function toggleCard(wId) {
  const card = document.querySelector(`.warning-card[data-id="${wId}"]`);
  if (card) {
    card.classList.toggle("open");
    if (card.classList.contains("open")) {
      setTimeout(() => {
        const flaggedEl = document.getElementById("flagged-" + wId);
        const srcBlock  = document.getElementById("src-" + wId);
        if (flaggedEl && srcBlock) srcBlock.scrollTop = Math.max(0, flaggedEl.offsetTop - 40);
      }, 80);
    }
  }
}
window.toggleCard = toggleCard;

function getRuleText(w) {
  const ctx = w.misra_context || w.retrieved_context || {};
  if (typeof ctx === "string") return ctx.slice(0, 600);
  if (Array.isArray(ctx) && ctx.length) {
    const chunk = ctx[0];
    return chunk.body_text || chunk.rule_text || chunk.text || chunk.amplification || "";
  }
  return ctx.body_text || ctx.rule_text || ctx.text || ctx.amplification || "";
}

function friendlyKey(k) {
  const MAP = { warning_id:"Warning ID", rule_id:"Rule", message:"Message", file_path:"File", severity:"Severity", checker_name:"Checker", misra_rule:"MISRA Rule", category:"Category", rule_category:"Rule Type" };
  return MAP[k] || k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function formatRuleId(raw) {
  if (!raw) return "";
  const m1 = raw.match(/RULE[-_](\d+)[-_](\d+)/i);
  if (m1) return `${m1[1]}.${m1[2]}`;
  const m2 = raw.match(/rule\s+(\d+[\._]\d+)/i);
  if (m2) return m2[1].replace("_", ".");
  const m3 = raw.match(/^(\d+)[_.](\d+)$/);
  if (m3) return `${m3[1]}.${m3[2]}`;
  return raw;
}

function escHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function baseName(path) {
  return (path || "").replace(/\\/g, "/").split("/").pop();
}

/* ── Run list search ── */
(function initIndexSearch() {
  const tbody = document.querySelector(".runs-table tbody");
  if (!tbody) return;
  const rows = Array.from(tbody.querySelectorAll("tr.run-row"));
  if (rows.length < 6) return;
  const panel = document.getElementById("runs-panel");
  if (!panel) return;
  const sw = document.createElement("div");
  sw.className = "search-wrap";
  sw.innerHTML = `<input class="run-search" type="search" placeholder="Filter by run ID…" aria-label="Filter runs"/>`;
  const table = panel.querySelector(".runs-table");
  if (table) panel.insertBefore(sw, table);
  sw.querySelector(".run-search").addEventListener("input", function () {
    const q = this.value.trim().toLowerCase();
    rows.forEach(row => {
      const id = (row.querySelector(".run-id-badge") || row).textContent.toLowerCase();
      row.style.display = (!q || id.includes(q)) ? "" : "none";
    });
  });
})();
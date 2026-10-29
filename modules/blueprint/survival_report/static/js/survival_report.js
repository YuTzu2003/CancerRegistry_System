(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const elements = {
    input: $("#survivalFiles"),
    dropZone: $("#dropZone"),
    queue: $("#fileQueue"),
    previewButton: $("#generatePreview"),
    status: $("#moduleStatus"),
    workspace: $("#previewWorkspace"),
    deckList: $("#deckList"),
    selectAllDecks: $("#selectAllDecks"),
    clearDeckSelection: $("#clearDeckSelection"),
    deckSelectionSummary: $("#deckSelectionSummary"),
    currentDeckSummary: $("#currentDeckSummary"),
    list: $("#reportList"),
    filter: $("#reportFilter"),
    preview: $("#reportPreview"),
    editor: $("#displayEditor"),
    displayTitle: $("#displayTitle"),
    customTitleToggle: $("#customTitleToggle"),
    hospitalEditors: $("#hospitalEditors"),
    cancerName: $("#cancerName"),
    stagingSystem: $("#stagingSystem"),
    issues: $("#issuePanel"),
    selectedSummary: $("#selectedSummary"),
    position: $("#previewPosition"),
    previous: $("#previousReport"),
    next: $("#nextReport"),
    pptx: $("#downloadPptx"),
  };

  if (!elements.input) return;

  const deckState = window.SurvivalDeckState;

  const state = {
    files: [],
    jobId: null,
    batch: null,
    currentDeckId: null,
    currentId: null,
    phase: "empty",
    draggedId: null,
    saveTimer: null,
  };

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const humanSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  function setPhase(phase, message = "", isError = false, failures = []) {
    state.phase = phase;
    elements.previewButton.disabled = !state.files.length || phase === "uploading" || phase === "exporting";
    elements.previewButton.innerHTML = phase === "uploading"
      ? '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>解析中…'
      : '<i class="bi bi-layout-text-window-reverse"></i>產生預覽';
    elements.status.hidden = !message && !failures.length;
    elements.status.replaceChildren();
    if (message) {
      const summary = document.createElement("div");
      summary.textContent = message;
      elements.status.append(summary);
    }
    if (failures.length) {
      const list = document.createElement("ul");
      list.className = "module-status__files";
      for (const failure of failures) {
        const item = document.createElement("li");
        item.textContent = `${failure.filename}：${failure.error}`;
        list.append(item);
      }
      elements.status.append(list);
    }
    elements.status.classList.toggle("error", isError);
  }

  function acceptFiles(fileList) {
    const incoming = Array.from(fileList).filter((file) => /\.(xls|xlsx)$/i.test(file.name));
    for (const file of incoming) {
      const duplicate = state.files.some((item) => item.name === file.name && item.size === file.size);
      if (!duplicate) state.files.push(file);
    }
    renderQueue();
    setPhase(state.files.length ? "ready" : "empty");
  }

  function renderQueue() {
    elements.queue.innerHTML = state.files.map((file, index) => `
      <div class="file-chip">
        <i class="bi bi-file-earmark-excel"></i>
        <div class="file-chip__meta">
          <strong title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</strong>
          <span>${humanSize(file.size)}</span>
        </div>
        <button type="button" data-remove-file="${index}" aria-label="移除 ${escapeHtml(file.name)}"><i class="bi bi-x-lg"></i></button>
      </div>
    `).join("");
  }

  elements.input.addEventListener("change", (event) => acceptFiles(event.target.files));
  elements.dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      elements.input.click();
    }
  });
  ["dragenter", "dragover"].forEach((name) => elements.dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("is-dragging");
  }));
  ["dragleave", "drop"].forEach((name) => elements.dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("is-dragging");
  }));
  elements.dropZone.addEventListener("drop", (event) => acceptFiles(event.dataTransfer.files));
  elements.queue.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-file]");
    if (!button) return;
    state.files.splice(Number(button.dataset.removeFile), 1);
    renderQueue();
    setPhase(state.files.length ? "ready" : "empty");
  });

  elements.previewButton.addEventListener("click", async () => {
    if (!state.files.length) return;
    setPhase("uploading", `正在解析 ${state.files.length} 個檔案…`);
    const form = new FormData();
    state.files.forEach((file) => form.append("files", file, file.name));
    try {
      const response = await fetch("/api/survival-report/preview", { method: "POST", body: form });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "無法建立預覽。");
      state.jobId = payload.job_id;
      state.batch = payload.batch;
      const initial = deckState.selectDeck(state.batch, deckState.orderedDecks(state.batch)[0]?.deck_id);
      state.currentDeckId = initial.deckId;
      state.currentId = initial.tableId;
      elements.workspace.hidden = false;
      renderAll();
      const fileStatus = deckState.previewFileStatus(payload.files);
      setPhase(
        "preview",
        fileStatus.message,
        fileStatus.failures.length > 0,
        fileStatus.failures,
      );
      elements.workspace.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setPhase("error", error.message || "發生未預期錯誤。", true);
    }
  });

  const currentDeck = () => deckState.currentDeck(state.batch, state.currentDeckId);
  const currentDeckTables = () => deckState.currentDeckTables(currentDeck(), "all");
  const currentTable = () => currentDeckTables().find((table) => table.table_id === state.currentId) || null;

  function visibleTables() {
    return deckState.currentDeckTables(currentDeck(), elements.filter.value);
  }

  function renderDeckList() {
    const decks = deckState.orderedDecks(state.batch);
    elements.deckList.innerHTML = decks.map((deck) => {
      const hospitals = deck.hospital_names?.join("、") || "未辨識醫院";
      const issueText = deck.warning_count ? `${deck.warning_count} 個警示` : `${deck.tables.length} 張投影片`;
      return `
        <article class="deck-card ${deck.deck_id === state.currentDeckId ? "active" : ""}"
          data-deck-id="${escapeHtml(deck.deck_id)}" tabindex="0">
          <input type="checkbox" data-select-deck="${escapeHtml(deck.deck_id)}" ${deck.selected ? "checked" : ""}
            aria-label="選取 ${escapeHtml(deck.period_start)}-${escapeHtml(deck.period_end)} ${escapeHtml(hospitals)}">
          <div class="deck-card__text">
            <strong>${escapeHtml(deck.period_start)}-${escapeHtml(deck.period_end)} · ${escapeHtml(hospitals)}</strong>
            <span>${escapeHtml(deck.target_years)} 年存活率 · ${escapeHtml(issueText)}</span>
          </div>
        </article>`;
    }).join("");
    const selected = decks.filter((deck) => deck.selected).length;
    elements.deckSelectionSummary.textContent = `${selected} / ${decks.length}`;
    elements.pptx.disabled = selected === 0;
  }

  function renderList() {
    const tables = visibleTables();
    elements.list.innerHTML = tables.map((table) => {
      return `
        <article class="report-card ${table.table_id === state.currentId ? "active" : ""}"
          data-table-id="${table.table_id}" draggable="true" tabindex="0">
          <div class="report-card__text">
            <strong>${escapeHtml(table.display_title)}</strong>
            <span>${escapeHtml(table.period_start)}-${escapeHtml(table.period_end)} · ${escapeHtml(table.hospitals.map((hospital) => hospital.display_name).join("、"))}</span>
          </div>
          ${table.issues.length ? `<span class="issue-count">${table.issues.length} 警示</span>` : ""}
        </article>`;
    }).join("");
    const deck = currentDeck();
    elements.selectedSummary.textContent = `${deck?.tables.length || 0} / ${deck?.tables.length || 0}`;
  }

  const rate = (estimate) => estimate.rate === null ? "-" : Number(estimate.rate).toFixed(2);
  const ci = (estimate) => estimate.ci_low === null || estimate.ci_high === null
    ? "-"
    : `( ${Number(estimate.ci_low).toFixed(2)} , ${Number(estimate.ci_high).toFixed(2)} )`;
  const unavailableEstimate = { rate: null, ci_low: null, ci_high: null, value_status: "not_available" };
  const hospitalEstimate = (row, hospitalKey) => (
    row.hospital_values.find((item) => item.hospital_key === hospitalKey)?.estimate || unavailableEstimate
  );

  const generatedTitle = (table) => {
    const cancer = table.cancer.trim();
    let staging = table.staging_system.trim();
    if (!staging || staging.toLowerCase() === "ajcc") return `${cancer}存活率`;
    if (!staging.endsWith("分期")) staging = `${staging}分期`;
    return `${cancer}${staging}存活率`;
  };

  function comparisonBanner(table) {
    const chineseYears = {
      1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
      6: "六", 7: "七", 8: "八", 9: "九", 10: "十",
    };
    const years = chineseYears[table.target_years] || String(table.target_years);
    const scope = table.hospitals.some((hospital) => hospital.is_local) ? "台大雲林與全國" : "全國";
    return `${table.period_start}-${table.period_end} 存活率：${scope}${years}年存活率比較（百分比）`;
  }

  function renderPreview() {
    const table = currentTable();
    const deck = currentDeck();
    const ordered = currentDeckTables();
    const position = table ? ordered.findIndex((item) => item.table_id === table.table_id) + 1 : 0;
    elements.position.textContent = `${position} / ${ordered.length}`;
    elements.previous.disabled = position <= 1;
    elements.next.disabled = position === 0 || position >= ordered.length;
    elements.currentDeckSummary.textContent = deck
      ? `${deck.period_start}-${deck.period_end} · ${(deck.hospital_names || []).join("、")}` : "";
    if (!table) {
      elements.editor.hidden = true;
      elements.issues.hidden = true;
      elements.preview.innerHTML = '<div class="empty-preview"><strong>此份 PPT 沒有可預覽的投影片</strong></div>';
      return;
    }
    elements.editor.hidden = false;
    elements.displayTitle.value = table.display_title;
    const titleUnlocked = Boolean(table.custom_title);
    elements.displayTitle.disabled = !titleUnlocked;
    elements.customTitleToggle.checked = titleUnlocked;
    elements.hospitalEditors.innerHTML = table.hospitals.map((hospital, index) => `
      <label>醫院名稱${table.hospitals.length > 1 ? ` ${index + 1}` : ""}
        <input type="text" maxlength="80" data-hospital-key="${escapeHtml(hospital.key)}" value="${escapeHtml(hospital.display_name)}">
      </label>`).join("");
    elements.cancerName.value = table.cancer;
    elements.stagingSystem.value = table.staging_system;
    const body = table.rows.map((row) => {
      const hospitalRates = table.hospitals.map((hospital) => {
        const className = hospital.key === table.primary_hospital_key ? "hospital-value" : "";
        return `<td class="${className}">${rate(hospitalEstimate(row, hospital.key))}</td>`;
      }).join("");
      const hospitalCis = table.hospitals.map((hospital) => {
        const className = hospital.key === table.primary_hospital_key ? "hospital-value" : "";
        return `<td class="${className}">${ci(hospitalEstimate(row, hospital.key))}</td>`;
      }).join("");
      return `
      <tr>
        <td rowspan="2"><strong>${escapeHtml(row.stage)}</strong></td>
        <td rowspan="2">${escapeHtml(row.stage_count ?? "-")}</td>
        <td rowspan="2">${escapeHtml(row.death_count ?? "-")}</td>
        ${hospitalRates}
        <td>${rate(row.nationwide)}</td>
        <td>${rate(row.medical_center)}</td>
        <td>${rate(row.non_medical_center)}</td>
      </tr>
      <tr class="ci-row">
        ${hospitalCis}
        <td>${ci(row.nationwide)}</td>
        <td>${ci(row.medical_center)}</td>
        <td>${ci(row.non_medical_center)}</td>
      </tr>`;
    }).join("");
    const hospitalHeaders = table.hospitals.map((hospital) => `<th>${escapeHtml(hospital.display_name)}<br>年齡調整（觀察）<br>存活率% · 95% CI</th>`).join("");
    const columns = ["7%", "8%", "8%", ...table.hospitals.map(() => "auto"), "auto", "auto", "auto"];
    const minimumWidth = Math.max(100, 46 + (table.hospitals.length * 14));
    elements.preview.innerHTML = `
      <h3 class="slide-preview__title">${escapeHtml(table.display_title)}</h3>
      <div class="slide-preview__table-wrap">
        <table class="slide-preview__table" style="min-width:${minimumWidth}%">
          <colgroup>${columns.map((width) => `<col style="width:${width}">`).join("")}</colgroup>
          <thead>
            <tr><th rowspan="2">期別</th><th colspan="${table.hospitals.length + 5}">${escapeHtml(comparisonBanner(table))}</th></tr>
            <tr><th>期別人數</th><th>死亡人數</th>${hospitalHeaders}<th>全國<br>年齡調整存活率%<br>95% CI</th><th>醫學中心<br>年齡調整存活率%<br>95% CI</th><th>非醫學中心<br>年齡調整存活率%<br>95% CI</th></tr>
          </thead><tbody>${body}</tbody>
        </table>
      </div>
      <div class="slide-preview__notes">
        <p>(1) 藍字：代表年齡層未滿 10 人，無法進行年齡標準化調整，故呈現觀察存活率及 95% CI。</p>
        <p>(2) 存活率顯示「-」代表無足夠個案可追蹤至目標年，或所有個案於目標年前死亡，無法計算。</p>
      </div>`;
    elements.issues.hidden = table.issues.length === 0;
    elements.issues.innerHTML = table.issues.length ? `<ul>${table.issues.map((issue) => `<li class="${issue.severity}"><strong>${issue.severity === "info" ? "資訊" : "警示"}</strong>：${escapeHtml(issue.message)}</li>`).join("")}</ul>` : "";
  }

  function renderAll() {
    renderDeckList();
    renderList();
    renderPreview();
  }

  elements.filter.addEventListener("change", renderList);
  function chooseDeck(deckId) {
    const selected = deckState.selectDeck(state.batch, deckId);
    state.currentDeckId = selected.deckId;
    state.currentId = selected.tableId;
    renderAll();
  }
  elements.deckList.addEventListener("click", (event) => {
    const checkbox = event.target.closest("[data-select-deck]");
    if (checkbox) {
      const deck = deckState.currentDeck(state.batch, checkbox.dataset.selectDeck);
      if (deck) deck.selected = checkbox.checked;
      renderDeckList();
      scheduleSave();
      event.stopPropagation();
      return;
    }
    const card = event.target.closest("[data-deck-id]");
    if (card) chooseDeck(card.dataset.deckId);
  });
  elements.deckList.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    if (event.target.matches("input")) return;
    const card = event.target.closest("[data-deck-id]");
    if (card) {
      event.preventDefault();
      chooseDeck(card.dataset.deckId);
    }
  });
  elements.selectAllDecks.addEventListener("click", () => {
    deckState.setAllDeckSelection(state.batch, true);
    renderDeckList();
    scheduleSave();
  });
  elements.clearDeckSelection.addEventListener("click", () => {
    deckState.setAllDeckSelection(state.batch, false);
    renderDeckList();
    scheduleSave();
  });
  elements.list.addEventListener("click", (event) => {
    const card = event.target.closest("[data-table-id]");
    if (card) {
      state.currentId = card.dataset.tableId;
      renderAll();
    }
  });
  elements.list.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const card = event.target.closest("[data-table-id]");
    if (card) {
      event.preventDefault();
      state.currentId = card.dataset.tableId;
      renderAll();
    }
  });
  elements.list.addEventListener("dragstart", (event) => {
    const card = event.target.closest("[data-table-id]");
    if (!card) return;
    state.draggedId = card.dataset.tableId;
    card.classList.add("dragging");
  });
  elements.list.addEventListener("dragend", (event) => {
    event.target.closest("[data-table-id]")?.classList.remove("dragging");
    state.draggedId = null;
  });
  elements.list.addEventListener("dragover", (event) => event.preventDefault());
  elements.list.addEventListener("drop", (event) => {
    event.preventDefault();
    const target = event.target.closest("[data-table-id]");
    if (!target || !state.draggedId || target.dataset.tableId === state.draggedId) return;
    const deck = currentDeck();
    if (!deck) return;
    const ordered = currentDeckTables();
    const from = ordered.findIndex((item) => item.table_id === state.draggedId);
    const to = ordered.findIndex((item) => item.table_id === target.dataset.tableId);
    const [moved] = ordered.splice(from, 1);
    ordered.splice(to, 0, moved);
    ordered.forEach((item, index) => { item.sort_order = index; });
    renderAll();
    scheduleSave();
  });

  function editCurrent(field, value) {
    const table = currentTable();
    if (!table) return;
    table[field] = value.trim();
    if ((field === "cancer" || field === "staging_system") && !table.custom_title) {
      table.display_title = generatedTitle(table);
    }
    renderList();
    renderPreview();
    scheduleSave();
  }
  elements.displayTitle.addEventListener("change", (event) => editCurrent("display_title", event.target.value));
  elements.customTitleToggle.addEventListener("change", (event) => {
    const table = currentTable();
    if (!table) return;
    table.custom_title = event.target.checked;
    if (!table.custom_title) table.display_title = generatedTitle(table);
    renderAll();
    if (table.custom_title) elements.displayTitle.focus();
    scheduleSave();
  });
  elements.hospitalEditors.addEventListener("change", (event) => {
    const input = event.target.closest("[data-hospital-key]");
    const table = currentTable();
    if (!input || !table) return;
    const hospital = table.hospitals.find((item) => item.key === input.dataset.hospitalKey);
    if (!hospital) return;
    hospital.display_name = input.value.trim();
    renderAll();
    scheduleSave();
  });
  elements.cancerName.addEventListener("change", (event) => editCurrent("cancer", event.target.value));
  elements.stagingSystem.addEventListener("change", (event) => editCurrent("staging_system", event.target.value));

  function movePreview(delta) {
    const ordered = currentDeckTables();
    const current = ordered.findIndex((item) => item.table_id === state.currentId);
    const target = ordered[current + delta];
    if (target) {
      state.currentId = target.table_id;
      renderAll();
    }
  }
  elements.previous.addEventListener("click", () => movePreview(-1));
  elements.next.addEventListener("click", () => movePreview(1));

  async function saveOverrides() {
    if (!state.jobId || !state.batch) return;
    const response = await fetch(`/api/survival-report/jobs/${state.jobId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decks: state.batch.decks.map((deck) => ({
          deck_id: deck.deck_id,
          selected: deck.selected,
          sort_order: deck.sort_order,
        })),
        tables: state.batch.decks.flatMap((deck) => deck.tables.map((table) => ({
          deck_id: deck.deck_id,
          table_id: table.table_id,
          hospitals: table.hospitals.map((hospital) => ({
            hospital_key: hospital.key,
            display_name: hospital.display_name,
          })),
          cancer: table.cancer,
          staging_system: table.staging_system,
          display_title: table.display_title,
          custom_title: Boolean(table.custom_title),
          selected: table.selected,
          sort_order: table.sort_order,
        }))),
      }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "無法儲存預覽設定。");
    state.batch = payload.batch;
    if (!deckState.currentDeck(state.batch, state.currentDeckId)) {
      const initial = deckState.selectDeck(state.batch, deckState.orderedDecks(state.batch)[0]?.deck_id);
      state.currentDeckId = initial.deckId;
      state.currentId = initial.tableId;
    } else if (!currentTable()) {
      state.currentId = currentDeckTables()[0]?.table_id || null;
    }
    renderAll();
  }

  function scheduleSave() {
    window.clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(() => saveOverrides().catch((error) => setPhase("error", error.message, true)), 500);
  }

  async function download(kind, fallbackFilename) {
    try {
      setPhase("exporting", "正在產生報表，請稍候…");
      await saveOverrides();
      const response = await fetch(`/api/survival-report/jobs/${state.jobId}/export/${kind}`, { method: "POST" });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.error || "下載失敗。");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = deckState.downloadFilename(response.headers.get("Content-Disposition"), fallbackFilename);
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setPhase("preview", "報表已完成下載。");
      renderAll();
    } catch (error) {
      setPhase("error", error.message || "下載失敗。", true);
    }
  }
  elements.pptx.addEventListener("click", () => download("pptx", "存活率報表.pptx"));
})();

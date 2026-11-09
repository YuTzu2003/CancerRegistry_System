(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.SurvivalDeckState = api;
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function orderedDecks(batch) {
    return [...(batch?.decks || [])].sort((a, b) => a.sort_order - b.sort_order);
  }

  function comparisonPeriods(batch) {
    const periods = new Map();
    for (const deck of batch?.decks || []) {
      const start = Number(deck.period_start);
      const end = Number(deck.period_end);
      if (!Number.isFinite(start) || !Number.isFinite(end)) continue;
      const value = `${start}-${end}`;
      periods.set(value, { value, label: value, start, end });
    }
    return [...periods.values()]
      .sort((a, b) => a.start - b.start || a.end - b.end)
      .map(({ value, label }) => ({ value, label }));
  }

  function currentDeck(batch, deckId) {
    return orderedDecks(batch).find((deck) => deck.deck_id === deckId) || null;
  }

  function currentDeckTables(deck, filter = "all") {
    return [...(deck?.tables || [])]
      .sort((a, b) => a.sort_order - b.sort_order)
      .filter((table) => {
        if (table.detail_visible === false) return false;
        if (filter === "warning") return table.issues.length > 0;
        return true;
      });
  }

  function selectDeck(batch, deckId) {
    const deck = currentDeck(batch, deckId);
    const table = currentDeckTables(deck, "all")[0] || null;
    return { deckId: deck?.deck_id || null, tableId: table?.table_id || null };
  }

  function setAllDeckSelection(batch, selected) {
    for (const deck of batch?.decks || []) {
      deck.selected = Boolean(selected);
    }
    return batch;
  }

  function downloadFilename(contentDisposition, fallback) {
    const header = String(contentDisposition || "");
    const encoded = header.match(/filename\*=UTF-8''([^;]+)/i);
    if (encoded) {
      try { return decodeURIComponent(encoded[1]); } catch (_) { return fallback; }
    }
    const quoted = header.match(/filename="([^"]+)"/i);
    if (quoted) return quoted[1];
    const plain = header.match(/filename=([^;]+)/i);
    return plain ? plain[1].trim() : fallback;
  }

  function previewFileStatus(files) {
    const failures = (files || [])
      .filter((file) => !file.ok)
      .map((file) => ({
        filename: file.filename || "未命名檔案",
        error: file.error || "檔案無法解析，請確認內容後重新上傳。",
      }));
    return {
      message: failures.length
        ? `預覽已建立；另有 ${failures.length} 個檔案未建立報表。`
        : "預覽已完成，請確認報表內容。",
      failures,
    };
  }

  function titleKey(value) {
    return String(value || "").normalize("NFKC").toLowerCase().replace(/[\s_\-－—]+/g, "");
  }

  function finalizedTitle(cancer, stagingSystem) {
    const key = `${titleKey(cancer)}|${titleKey(stagingSystem)}`;
    const titles = {
      "大腸癌all|ajcc": "結腸直腸癌-ALL存活率",
      "大腸癌結腸癌|ajcc": "結腸癌存活率",
      "大腸癌直腸癌|ajcc": "直腸癌存活率",
      "子宮頸癌|figo": "子宮頸癌存活率",
      "子宮體癌|figo": "子宮體癌存活率",
      "卵巢癌|figo": "卵巢癌FIGO分期存活率",
      "女性乳癌|ajcc": "乳癌存活率",
      "肺癌非小細胞癌all|ajcc": "肺癌 非小細胞癌-ALL存活率",
      "肺癌非小細胞癌腺癌|ajcc": "肺癌 非小細胞癌-腺癌存活率",
      "肺癌非小細胞癌鱗狀細胞癌|ajcc": "肺癌 非小細胞癌-鱗狀細胞癌存活率",
      "肺癌小細胞癌|ajcc": "肺癌-小細胞癌存活率",
      "食道癌|ajcc": "食道癌存活率",
      "肝癌|bclc": "肝癌BCLC分期存活率",
      "胃癌|ajcc": "胃癌存活率",
      "鼻咽癌|ajcc": "鼻咽癌存活率",
      "口腔癌|ajcc": "口腔癌存活率",
      "下咽癌|ajcc": "下咽癌存活率",
      "喉癌|ajcc": "喉癌存活率",
      "口咽癌p16+|ajcc": "口咽癌_P16+存活率",
      "口咽癌p16|ajcc": "口咽癌_P16-癌存活率",
      "膀胱癌|ajcc": "膀胱癌存活率",
      "攝護腺癌|ajcc": "攝護腺癌存活率",
    };
    if (titles[key]) return titles[key];
    const cancerLabel = String(cancer || "").trim();
    let staging = String(stagingSystem || "").trim();
    if (!staging || staging.toLowerCase() === "ajcc") return `${cancerLabel}存活率`;
    if (!staging.endsWith("分期")) staging = `${staging}分期`;
    return `${cancerLabel}${staging}存活率`;
  }

  return {
    orderedDecks,
    comparisonPeriods,
    currentDeck,
    currentDeckTables,
    selectDeck,
    setAllDeckSelection,
    downloadFilename,
    previewFileStatus,
    finalizedTitle,
  };
}));

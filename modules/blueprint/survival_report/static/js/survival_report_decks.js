(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.SurvivalDeckState = api;
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function orderedDecks(batch) {
    return [...(batch?.decks || [])].sort((a, b) => a.sort_order - b.sort_order);
  }

  function currentDeck(batch, deckId) {
    return orderedDecks(batch).find((deck) => deck.deck_id === deckId) || null;
  }

  function currentDeckTables(deck, filter = "all") {
    return [...(deck?.tables || [])]
      .sort((a, b) => a.sort_order - b.sort_order)
      .filter((table) => {
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
        : "預覽已建立，請確認內容與警示。",
      failures,
    };
  }

  return {
    orderedDecks,
    currentDeck,
    currentDeckTables,
    selectDeck,
    setAllDeckSelection,
    downloadFilename,
    previewFileStatus,
  };
}));

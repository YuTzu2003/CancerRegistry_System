const nationalSelectAll = document.getElementById("nationalSelectAll");
  const nationalRowSelections = document.querySelectorAll(".national-row-select");
  if (nationalSelectAll) {
    nationalSelectAll.addEventListener("change", () => nationalRowSelections.forEach((checkbox) => { checkbox.checked = nationalSelectAll.checked; }));
    nationalRowSelections.forEach((checkbox) => checkbox.addEventListener("change", () => {
      nationalSelectAll.checked = nationalRowSelections.length > 0 && [...nationalRowSelections].every((item) => item.checked);
    }));
  }

  const nationalTable = document.querySelector(".national-table");
  if (nationalTable) {
    const headers = nationalTable.querySelectorAll("th.sortable-header");
    headers.forEach((header) => header.addEventListener("click", () => {
      const tbody = nationalTable.querySelector("tbody");
      const rows = Array.from(tbody.querySelectorAll("tr:not(.national-empty-row)"));
      const index = Number(header.dataset.sortIdx);
      const ascending = header.classList.contains("sort-asc");
      headers.forEach((item) => {
        item.classList.remove("sort-asc", "sort-desc");
        item.querySelector("i").className = "bi bi-caret-down text-muted ms-1";
      });
      header.classList.add(ascending ? "sort-desc" : "sort-asc");
      header.querySelector("i").className = ascending ? "bi bi-caret-down-fill text-dark ms-1" : "bi bi-caret-up-fill text-dark ms-1";
      rows.sort((left, right) => {
        const leftValue = left.children[index].innerText.trim();
        const rightValue = right.children[index].innerText.trim();
        const leftNumber = Number(leftValue);
        const rightNumber = Number(rightValue);
        if (!Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)) return ascending ? rightNumber - leftNumber : leftNumber - rightNumber;
        return ascending ? rightValue.localeCompare(leftValue, "zh-TW") : leftValue.localeCompare(rightValue, "zh-TW");
      });
      rows.forEach((row) => tbody.appendChild(row));
    }));
  }

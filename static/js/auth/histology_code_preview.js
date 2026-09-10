document.addEventListener("DOMContentLoaded", function() {
    const successAlert = document.querySelector(".alert-success");
    if (successAlert && window.Swal) {
      const message = successAlert.textContent.trim();
      successAlert.remove();
      Swal.fire({ icon: "success", title: "儲存成功", text: message, confirmButtonColor: "#2563eb" });
    }
    const dangerAlert = document.querySelector(".alert-danger");
    if (dangerAlert && window.Swal) {
      const message = dangerAlert.textContent.trim();
      dangerAlert.remove();
      Swal.fire({ icon: "error", title: "發生錯誤", text: message, confirmButtonColor: "#2563eb" });
    }
  });

  const selectAll = document.getElementById("histologySelectAll");
  const rowSelections = document.querySelectorAll(".histology-row-select");

  if (selectAll) {
    selectAll.addEventListener("change", () => {
      rowSelections.forEach((checkbox) => {
        checkbox.checked = selectAll.checked;
      });
    });

    rowSelections.forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        selectAll.checked = rowSelections.length > 0 && [...rowSelections].every((item) => item.checked);
      });
    });
  }

  // Table Sorting Logic
  const histologyTable = document.querySelector(".histology-table");
  if (histologyTable) {
    const headers = histologyTable.querySelectorAll("th.sortable-header");
    headers.forEach(header => {
      header.addEventListener("click", () => {
        const tbody = histologyTable.querySelector("tbody");
        const rows = Array.from(tbody.querySelectorAll("tr:not(.histology-empty-row)"));
        if (rows.length === 0) return;
        
        const idx = parseInt(header.getAttribute("data-sort-idx"));
        const isAsc = header.classList.contains("sort-asc");
        
        // Reset all headers
        headers.forEach(h => {
          h.classList.remove("sort-asc", "sort-desc");
          const icon = h.querySelector("i.bi");
          if (icon) icon.className = "bi bi-caret-down text-muted ms-1";
        });
        
        // Set current header state
        header.classList.add(isAsc ? "sort-desc" : "sort-asc");
        const currIcon = header.querySelector("i.bi");
        if (currIcon) {
          currIcon.className = isAsc ? "bi bi-caret-down-fill text-dark ms-1" : "bi bi-caret-up-fill text-dark ms-1";
        }
        
        // Sort rows
        rows.sort((a, b) => {
          const getVal = (row) => {
            const cell = row.children[idx];
            if (!cell) return "";
            const input = cell.querySelector("input:not([type='hidden']):not([type='checkbox'])");
            return input ? input.value.trim() : cell.innerText.trim();
          };
          
          const aCol = getVal(a);
          const bCol = getVal(b);
          
          const aNum = parseFloat(aCol);
          const bNum = parseFloat(bCol);
          
          if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAsc ? bNum - aNum : aNum - bNum;
          }
          return isAsc ? bCol.localeCompare(aCol, "zh-TW") : aCol.localeCompare(bCol, "zh-TW");
        });
        
        // Append sorted rows
        rows.forEach(row => tbody.appendChild(row));
      });
    });
  }

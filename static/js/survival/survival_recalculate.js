document.querySelector(".recalc-index")?.addEventListener("click", (event) => {
  const link = event.target.closest("a");
  if (!link) return;

  const cancer = document.getElementById(link.hash.slice(1));
  if (cancer) cancer.open = true;
});

const fileInput = document.getElementById("case-file");
const filters = document.getElementById("recalc-filters");
const hospital = document.getElementById("recalc-hospital");
const startYear = document.getElementById("recalc-start-year");
const endYear = document.getElementById("recalc-end-year");
const statusMessage = document.getElementById("recalc-file-status");
const submitButton = fileInput.form.querySelector('button[type="submit"]');
let hospitals = [];
let pendingRequest;

function updateEndYears() {
  const years = hospitals[hospital.selectedIndex].years;
  const previous = Number(endYear.value);
  endYear.replaceChildren(...years.filter(year => year >= Number(startYear.value))
    .map(year => new Option(year, year)));
  endYear.value = years.includes(previous) && previous >= Number(startYear.value) ? previous : years.at(-1);
}

function updateYears() {
  const years = hospitals[hospital.selectedIndex].years;
  startYear.replaceChildren(...years.map(year => new Option(year, year)));
  endYear.replaceChildren();
  updateEndYears();
}

hospital.addEventListener("change", updateYears);
startYear.addEventListener("change", updateEndYears);
fileInput.addEventListener("change", async () => {
  pendingRequest?.abort();
  const file = fileInput.files[0];
  document.getElementById("recalc-file-name").textContent = file?.name || "尚未選擇檔案";
  filters.hidden = true;
  submitButton.disabled = true;
  statusMessage.textContent = file ? "正在讀取院所及年度…" : "";
  if (!file) return;

  const controller = new AbortController();
  pendingRequest = controller;
  const body = new FormData();
  body.append("case_file", file);
  try {
    const response = await fetch(filters.dataset.optionsUrl, { method: "POST", body, signal: controller.signal });
    const data = await response.json();
    if (controller.signal.aborted) return;
    if (!response.ok) throw new Error(data.error || "無法讀取清單。");
    hospitals = data.hospitals;
    hospital.replaceChildren(...hospitals.map(item => new Option(item.label, item.label)));
    updateYears();
    filters.hidden = false;
    submitButton.disabled = false;
    statusMessage.textContent = "";
  } catch (error) {
    if (!controller.signal.aborted) statusMessage.textContent = error.message;
  }
});

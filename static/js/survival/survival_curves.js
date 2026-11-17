const fileInput = document.getElementById("case-file");
const filters = document.getElementById("recalc-filters");
const hospital = document.getElementById("recalc-hospital");
const startYear = document.getElementById("recalc-start-year");
const endYear = document.getElementById("recalc-end-year");
const statusMessage = document.getElementById("recalc-file-status");
const form = document.getElementById("curves-form");
const submitButton = form.querySelector('button[type="submit"]');
const errorBox = document.getElementById("curves-error");
const resultsBox = document.getElementById("curves-results");
const cancerSelect = document.getElementById("curves-cancer");

const STAGE_ORDER = ["All", "I", "II", "III", "IV"];
const STAGE_LABELS = { All: "不分期別", I: "第1期", II: "第2期", III: "第3期", IV: "第4期" };
const STAGE_COLORS = { All: "#2563eb", I: "#16a34a", II: "#d97706", III: "#ea580c", IV: "#dc2626" };

let hospitals = [];
let pendingRequest;
let payload = null;
let chart = null;

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

function resetFilters() {
  for (const field of [hospital, startYear, endYear]) {
    field.replaceChildren(new Option("請先讀取檔案", ""));
    field.disabled = true;
  }
}

hospital.addEventListener("change", updateYears);
startYear.addEventListener("change", updateEndYears);

fileInput.addEventListener("change", async () => {
  pendingRequest?.abort();
  const file = fileInput.files[0];
  document.getElementById("recalc-file-name").textContent = file?.name || "尚未選擇檔案";
  resetFilters();
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
    hospital.disabled = false;
    startYear.disabled = false;
    endYear.disabled = false;
    updateYears();
    submitButton.disabled = false;
    statusMessage.textContent = "";
  } catch (error) {
    if (!controller.signal.aborted) statusMessage.textContent = error.message;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;
  submitButton.disabled = true;
  statusMessage.textContent = "計算中…";
  const body = new FormData(form);
  try {
    const response = await fetch(filters.dataset.curvesUrl, { method: "POST", body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "計算失敗。");
    payload = data;
    renderResults();
  } catch (error) {
    errorBox.querySelector("span").textContent = error.message;
    errorBox.hidden = false;
    resultsBox.hidden = true;
  } finally {
    submitButton.disabled = false;
    statusMessage.textContent = "";
  }
});

function renderResults() {
  resultsBox.hidden = false;
  document.getElementById("curves-count").textContent = `${payload.results.length} 種癌別`;
  const index = document.getElementById("curves-index");
  index.replaceChildren(...payload.results.map((item, i) => {
    const link = document.createElement("a");
    link.href = "#curves-chart";
    link.textContent = item.name;
    link.addEventListener("click", () => { cancerSelect.selectedIndex = i; renderCancer(); });
    return link;
  }));
  cancerSelect.replaceChildren(...payload.results.map((item, i) =>
    new Option(`${item.name}（${item.cancer}）`, i)));
  renderCancer();
}

cancerSelect.addEventListener("change", renderCancer);

function clampCurve(points) {
  const kept = points.filter(([x]) => x <= 60);
  if (!kept.length) return kept;
  const last = points[points.length - 1];
  if (last[0] > 60) kept.push([60, kept[kept.length - 1][1]]);
  return kept;
}

function renderCancer() {
  const item = payload.results[Number(cancerSelect.value) || cancerSelect.selectedIndex];
  if (!item) return;
  renderChart(item);
  renderSummaryTable(item);
  renderLifeTables(item);
}

function renderChart(item) {
  if (!chart) {
    chart = echarts.init(document.getElementById("curves-chart"));
    window.addEventListener("resize", () => chart.resize());
  }
  const series = [];
  const legendData = [];
  STAGE_ORDER.forEach((stage) => {
    const block = item.stages[stage];
    if (!block) return;
    const color = STAGE_COLORS[stage];
    const name = `${STAGE_LABELS[stage]} (n=${block.n})`;
    legendData.push(name);
    series.push({
      name,
      type: "line",
      step: "end",
      showSymbol: false,
      lineStyle: { width: 2, color },
      itemStyle: { color },
      data: clampCurve(block.points),
      emphasis: { focus: "series" },
      z: 2,
    });
    const censors = block.censors.filter(([x]) => x <= 60);
    if (censors.length) {
      const censorName = `${STAGE_LABELS[stage]}-設限`;
      legendData.push(censorName);
      series.push({
        name: censorName,
        type: "scatter",
        symbol: "path://M0,-6 L0,6 M-6,0 L6,0",
        symbolSize: 9,
        itemStyle: { color: "transparent", borderColor: color, borderWidth: 1.5 },
        data: censors,
        tooltip: { show: false },
        z: 3,
      });
    }
  });
  chart.setOption({
    title: {
      text: `民國${payload.start_year}–${payload.end_year}年 ${item.name}（N=${item.total}）`,
      left: "center",
      textStyle: { fontSize: 15, fontWeight: 700 },
    },
    tooltip: {
      trigger: "axis",
      valueFormatter: value => (value == null ? "-" : `${(value * 100).toFixed(1)}%`),
    },
    legend: { type: "scroll", orient: "vertical", right: 0, top: 44, data: legendData },
    grid: { left: 64, right: 170, top: 48, bottom: 52 },
    xAxis: {
      type: "value", name: "Surv_Months", min: 0, max: 60, interval: 12,
      nameLocation: "middle", nameGap: 30,
    },
    yAxis: {
      type: "value", name: "Cum Survival", min: 0, max: 1,
      axisLabel: { formatter: value => `${(value * 100).toFixed(0)}%` },
    },
    series,
  }, true);
}

function formatRate(rate) {
  return rate == null ? "NA" : rate.toFixed(1);
}

function renderSummaryTable(item) {
  const table = document.getElementById("curves-summary-table");
  const rows = ["I", "II", "III", "IV", "All"].filter(stage => item.stages[stage]).map((stage) => {
    const block = item.stages[stage];
    return `<tr>
      <td class="recalc-td-stage"><strong>${STAGE_LABELS[stage]}</strong></td>
      <td>${block.n}</td>
      <td>${block.deaths}</td>
      <td>${block.censored}</td>
      ${block.annual.map(rate => `<td class="recalc-td-rate">${formatRate(rate)}</td>`).join("")}
    </tr>`;
  });
  table.innerHTML = `
    <thead>
      <tr>
        <th rowspan="2">期別</th><th rowspan="2">個案數</th><th rowspan="2">死亡</th><th rowspan="2">設限<br>(存活)</th>
        <th colspan="5">觀察存活率 %（Kaplan–Meier）</th>
      </tr>
      <tr><th>1年</th><th>2年</th><th>3年</th><th>4年</th><th>5年</th></tr>
    </thead>
    <tbody>${rows.join("")}</tbody>`;
}

function renderLifeTables(item) {
  const host = document.getElementById("curves-life-tables");
  host.replaceChildren(...STAGE_ORDER.filter(stage => item.stages[stage]).map((stage) => {
    const block = item.stages[stage];
    const wrap = document.createElement("div");
    wrap.className = "curves-life-table";
    wrap.innerHTML = `
      <h3>${STAGE_LABELS[stage]}（n = ${block.n}）</h3>
      <div class="recalc-report-scroll">
        <table class="recalc-report-table">
          <thead><tr>
            <th>月數區間</th><th>進入人數</th><th>死亡</th><th>設限</th><th>區間存活率 %</th><th>累積存活率 %</th>
          </tr></thead>
          <tbody>${block.life_table.map(row => `
            <tr>
              <td>${row.months}</td><td>${row.at_risk}</td><td>${row.deaths}</td><td>${row.censored}</td>
              <td>${row.interval == null ? "NA" : row.interval.toFixed(1)}</td>
              <td class="recalc-td-rate">${row.cumulative == null ? "NA" : row.cumulative.toFixed(1)}</td>
            </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
    return wrap;
  }));
}

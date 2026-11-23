const fileInput = document.getElementById("case-file");
const filters = document.getElementById("recalc-filters");
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
const STAGE_COLOR_TOKENS = {
  All: "--curves-stage-all",
  I: "--curves-stage-i",
  II: "--curves-stage-ii",
  III: "--curves-stage-iii",
  IV: "--curves-stage-iv",
};
const CHART_TOOLBOX = {
  right: 16,
  top: 0,
  feature: {
    dataView: { show: true, readOnly: false, title: "資料檢視", lang: ["資料檢視", "關閉", "重新整理"] },
    saveAsImage: { show: true, title: "下載圖片" },
  },
};

let availableYears = [];
let pendingRequest;
let payload = null;
let chart = null;

function chartPalette() {
  const style = getComputedStyle(document.querySelector(".survival-curves"));
  const value = name => style.getPropertyValue(name).trim();
  return {
    ink: value("--curves-chart-ink"),
    muted: value("--curves-chart-muted"),
    rule: value("--curves-chart-rule"),
    surface: value("--curves-chart-surface"),
    stages: Object.fromEntries(Object.entries(STAGE_COLOR_TOKENS)
      .map(([stage, token]) => [stage, value(token)])),
  };
}

function updateEndYears() {
  const years = availableYears;
  const previous = Number(endYear.value);
  endYear.replaceChildren(...years.filter(year => year >= Number(startYear.value))
    .map(year => new Option(year, year)));
  endYear.value = years.includes(previous) && previous >= Number(startYear.value) ? previous : years.at(-1);
}

function updateYears() {
  const years = availableYears;
  startYear.replaceChildren(...years.map(year => new Option(year, year)));
  endYear.replaceChildren();
  updateEndYears();
}

function resetFilters() {
  for (const field of [startYear, endYear]) {
    field.replaceChildren(new Option("請先讀取檔案", ""));
    field.disabled = true;
  }
}

startYear.addEventListener("change", updateEndYears);

fileInput.addEventListener("change", async () => {
  pendingRequest?.abort();
  const file = fileInput.files[0];
  document.getElementById("recalc-file-name").textContent = file?.name || "尚未選擇檔案";
  resetFilters();
  submitButton.disabled = true;
  statusMessage.textContent = file ? "正在讀取年度…" : "";
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
    availableYears = [...new Set(data.hospitals.flatMap(item => item.years))].sort((a, b) => a - b);
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
  renderLifeTables(item);
}

function renderChart(item) {
  if (!chart) {
    chart = echarts.init(document.getElementById("curves-chart"));
    window.addEventListener("resize", () => chart.resize());
  }
  const palette = chartPalette();
  const series = [];
  const legendData = [];
  STAGE_ORDER.forEach((stage) => {
    const block = item.stages[stage];
    if (!block) return;
    const color = palette.stages[stage];
    const name = STAGE_LABELS[stage];
    legendData.push(name);
    series.push({
      name,
      type: "line",
      step: "end",
      symbol: "emptyCircle",
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
      text: `${payload.start_year}-${payload.end_year}年${item.name}存活率曲線圖`,
      subtext: "資料來源：癌症登記資料庫",
      left: "center", top: 0,
      textStyle: { color: palette.ink, fontSize: 18, fontWeight: 700 },
      subtextStyle: { color: palette.muted, fontSize: 12 },
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line", lineStyle: { color: palette.muted, type: "solid", width: 1 } },
      backgroundColor: palette.surface,
      borderColor: palette.rule,
      borderWidth: 1,
      textStyle: { color: palette.ink },
      valueFormatter: value => (value == null ? "-" : `${(value * 100).toFixed(1)}%`),
    },
    toolbox: CHART_TOOLBOX,
    legend: {
      type: "plain", orient: "vertical", right: 20, top: "middle", data: legendData,
      textStyle: { color: palette.muted, fontSize: 13, lineHeight: 22 },
      itemWidth: 24, itemHeight: 14, itemGap: 8,
    },
    grid: { left: 16, right: 196, top: 88, bottom: 44, containLabel: true },
    xAxis: {
      type: "value", name: "Surv_Months", min: 0, max: 60, interval: 12,
      nameLocation: "middle", nameGap: 30,
      nameTextStyle: { color: palette.muted, fontSize: 13 },
      axisLine: { lineStyle: { color: palette.rule } },
      axisTick: { show: false },
      axisLabel: { color: palette.muted, fontSize: 12 },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value", name: "Cum Survival", min: 0, max: 1,
      nameTextStyle: { color: palette.muted, fontSize: 13 },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: palette.muted, formatter: value => `${(value * 100).toFixed(0)}%` },
      splitLine: { lineStyle: { color: palette.rule, type: "solid" } },
    },
    series,
  }, true);
}

function renderLifeTables(item) {
  document.getElementById("curves-life-caption").textContent =
    `表、${payload.start_year}–${payload.end_year}年${item.name}存活率生命表`;
  const host = document.getElementById("curves-life-tables");
  host.replaceChildren(...STAGE_ORDER.filter(stage => item.stages[stage]).map((stage) => {
    const block = item.stages[stage];
    const wrap = document.createElement("div");
    wrap.className = "curves-life-table";
    wrap.innerHTML = `
      <h3>${STAGE_LABELS[stage]}（n = ${block.n}）</h3>
      <div class="annual-report-table-wrap">
        <table class="annual-report-table">
          <thead><tr>
            <th>月數區間</th><th>進入人數</th><th>死亡</th><th>設限</th><th>區間存活率 %</th><th>累積存活率 %</th>
          </tr></thead>
          <tbody>${block.life_table.map(row => `
            <tr>
              <td>${row.months}</td><td>${row.at_risk}</td><td>${row.deaths}</td><td>${row.censored}</td>
              <td>${row.interval == null ? "NA" : row.interval.toFixed(1)}</td>
              <td>${row.cumulative == null ? "NA" : row.cumulative.toFixed(1)}</td>
            </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
    return wrap;
  }));
}

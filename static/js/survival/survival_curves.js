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
const SEX_ORDER = ["1", "2"];
const SEX_COLOR_TOKENS = { 1: "--curves-sex-1", 2: "--curves-sex-2" };
const RISK_CHECKPOINTS = [0, 12, 24, 36, 48, 60];
const CHART_TOOLBOX = {
  right: 16,
  top: 0,
  feature: {
    dataView: { show: true, readOnly: true, title: "資料檢視", lang: ["資料檢視", "關閉", "重新整理"], ...window.EChartsDataView.viewOnly },
    saveAsImage: { show: true, title: "下載圖片" },
  },
};

let availableYears = [];
let pendingRequest;
let payload = null;
let chart = null;
let sexChart = null;
let riskChart = null;
let activeView = "stage";

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
    sex: Object.fromEntries(Object.entries(SEX_COLOR_TOKENS)
      .map(([key, token]) => [key, value(token)])),
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


function currentItem() {
  return payload?.results[Number(cancerSelect.value) || cancerSelect.selectedIndex] || null;
}

function renderCancer() {
  const item = currentItem();
  if (!item) return;
  if (activeView === "sex") {
    renderSexChart(item);
    renderRiskChart(item);
  } else {
    renderChart(item);
    renderLifeTables(item);
  }
}

document.querySelectorAll(".curves-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const view = tab.dataset.view;
    if (view === activeView) return;
    activeView = view;
    document.querySelectorAll(".curves-tab").forEach((button) => {
      const selected = button === tab;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-selected", String(selected));
    });
    document.querySelectorAll(".curves-view").forEach((pane) => {
      pane.hidden = pane.dataset.view !== view;
    });
    document.getElementById("curves-risk-card").hidden = view !== "sex";
    renderCancer();
  });
});

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

function formatPValue(p) {
  if (p == null) return "p = NA";
  if (p < 0.0001) return "p < 0.0001";
  return `p = ${p.toFixed(4)}`;
}

function renderSexChart(item) {
  if (!sexChart) {
    sexChart = echarts.init(document.getElementById("curves-sex-chart"));
    window.addEventListener("resize", () => sexChart.resize());
  }
  const palette = chartPalette();
  const order = SEX_ORDER.filter(key => item.sexes && item.sexes[key]);
  const series = [];
  const legendData = [];
  const medianLines = [{ yAxis: 0.5 }];

  order.forEach((key) => {
    const block = item.sexes[key];
    const color = palette.sex[key];
    const name = `sex=${key}`;
    legendData.push(name);

    const lower = clampCurve(block.ci_lower);
    const upper = clampCurve(block.ci_upper);
    series.push({
      name: `__ci_band_${key}`, type: "custom", silent: true, z: 1,
      encode: { x: [0, 1], y: [2, 3] },
      data: lower.slice(0, -1).map(([start, low], index) =>
        [start, lower[index + 1][0], low, upper[index][1]]),
      renderItem: (_params, api) => {
        const top = api.coord([api.value(0), api.value(3)]);
        const bottom = api.coord([api.value(1), api.value(2)]);
        return { type: "rect", shape: {
          x: top[0], y: top[1], width: bottom[0] - top[0], height: bottom[1] - top[1],
        }, style: { fill: color, opacity: 0.18 } };
      },
    });

    series.push({
      name, type: "line", step: "end", symbol: "emptyCircle", showSymbol: false,
      lineStyle: { width: 2, color }, itemStyle: { color },
      data: clampCurve(block.points), emphasis: { focus: "series" }, z: 3,
    });

    const censors = block.censors.filter(([x]) => x <= 60);
    if (censors.length) {
      series.push({
        name: `__censor_${key}`, type: "scatter", symbol: "path://M0,-6 L0,6 M-6,0 L6,0",
        symbolSize: 9, itemStyle: { color: "transparent", borderColor: color, borderWidth: 1.5 },
        data: censors, tooltip: { show: false }, legendHoverLink: false, z: 4,
      });
    }

    if (block.median != null && block.median <= 60) {
      medianLines.push({ xAxis: block.median, lineStyle: { color } });
    }

  });

  // Median crosshair lines ride on the first curve series (grid 0).
  const firstCurve = series.find(entry => /^sex=/.test(entry.name));
  if (firstCurve) {
    firstCurve.markLine = {
      silent: true, symbol: "none",
      lineStyle: { type: "dashed", color: palette.muted, width: 1 },
      label: { show: false }, data: medianLines,
    };
  }

  sexChart.setOption({
    title: {
      text: `${payload.start_year}-${payload.end_year}年${item.name}性別存活率曲線圖`,
      subtext: `資料來源：癌症登記資料庫　${formatPValue(item.logrank_p)}`,
      left: "center", top: 0,
      textStyle: { color: palette.ink, fontSize: 18, fontWeight: 700 },
      subtextStyle: { color: palette.muted, fontSize: 12 },
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line", lineStyle: { color: palette.muted, type: "solid", width: 1 } },
      backgroundColor: palette.surface, borderColor: palette.rule, borderWidth: 1,
      textStyle: { color: palette.ink },
      formatter: (params) => {
        const rows = params.filter(entry => /^sex=/.test(entry.seriesName));
        if (!rows.length) return "";
        const head = `第 ${Number(rows[0].axisValue).toFixed(0)} 個月`;
        return head + rows.map(entry =>
          `<br/>${entry.marker}${entry.seriesName}: ${(entry.value[1] * 100).toFixed(1)}%`).join("");
      },
    },
    toolbox: CHART_TOOLBOX,
    legend: {
      type: "plain", orient: "horizontal", left: "center", bottom: 2, data: legendData,
      textStyle: { color: palette.muted, fontSize: 13, lineHeight: 22 },
      itemWidth: 24, itemHeight: 14, itemGap: 8,
    },
    grid: { left: 16, right: 24, top: 90, bottom: 86, containLabel: true },
    xAxis: {
      type: "value", name: "追蹤月數（月）", min: 0, max: 60, interval: 12,
      nameLocation: "middle", nameGap: 28, nameTextStyle: { color: palette.muted, fontSize: 13 },
      axisLine: { lineStyle: { color: palette.rule } }, axisTick: { show: false },
      axisLabel: { color: palette.muted, fontSize: 12 }, splitLine: { show: false },
    },
    yAxis: {
      type: "value", name: "累積存活率", min: 0, max: 1,
      nameGap: 18, nameLocation: "end", nameTextStyle: { color: palette.muted, fontSize: 13 },
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: palette.muted, formatter: value => `${(value * 100).toFixed(0)}%` },
      splitLine: { lineStyle: { color: palette.rule, type: "solid" } },
    },
    series,
  }, true);
  sexChart.resize();
}

function renderRiskChart(item) {
  if (!riskChart) {
    riskChart = echarts.init(document.getElementById("curves-risk-chart"));
    window.addEventListener("resize", () => {
      riskChart.resize();
      if (activeView === "sex") renderRiskChart(currentItem());
    });
  }
  const palette = chartPalette();
  const order = SEX_ORDER.filter(key => item.sexes && item.sexes[key]);
  const compact = riskChart.getWidth() < 420;
  riskChart.setOption({
    tooltip: { show: false },
    grid: { left: 16, right: 16, top: 16, bottom: 52, containLabel: true },
    xAxis: { type: "category", name: "追蹤月數（月）", nameLocation: "middle", nameGap: 26,
      data: RISK_CHECKPOINTS.map(String), nameTextStyle: { color: palette.muted, fontSize: 13 },
      axisLine: { lineStyle: { color: palette.rule } }, axisTick: { show: false },
      axisLabel: { color: palette.muted, fontSize: 12 },
      splitLine: { show: true, lineStyle: { color: palette.rule } } },
    yAxis: { type: "category", data: order.map(key => `sex=${key}`).reverse(),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: palette.muted, fontSize: 13, margin: 14 },
      splitLine: { show: true, lineStyle: { color: palette.rule } } },
    series: order.map(key => ({
      name: `sex=${key}`, type: "scatter", symbolSize: 2, silent: true,
      itemStyle: { color: "transparent" },
      data: RISK_CHECKPOINTS.map((month, index) => [String(month), `sex=${key}`, item.sexes[key].risk[index]]),
      label: { show: true, position: "top", distance: -10, color: palette.surface,
        fontSize: compact ? 11 : 13, fontWeight: 700,
        backgroundColor: palette.sex[key], padding: compact ? [5, 5] : [6, 10],
        borderRadius: 6, formatter: params => params.value[2] },
    })),
  }, true);
  riskChart.resize();
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

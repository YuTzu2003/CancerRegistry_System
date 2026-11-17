import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.utils import survival_table_from_events

CANCERS = ['Oral cavity','Oropharynx','Hypopharynx','Nasopharynx','Colon and Rectum',
           'Liver','Pancreas','Lung','Breast','Cervix','Esophagus','Stomach',
           'Bladder','Corpus','Ovary','Prostate','Larynx']
STAGES = ['All', 'I', 'II', 'III', 'IV']


def km_curve(d):
    """回傳 (ts_months, ss, censor_points)。censor_points 為 [(years, survival_at_time), ...]."""
    if len(d) == 0:
        return [], [], []
    f = KaplanMeierFitter().fit(d.Surv_Months.to_numpy(float),
                                event_observed=d.event.to_numpy(int))
    ts = f.survival_function_.index.to_numpy(float).tolist()
    ss = f.survival_function_.iloc[:, 0].to_numpy(float).tolist()
    # 設限時間：event == 0 的 Surv_Months
    censor_times = sorted(d.loc[d.event.eq(0), 'Surv_Months'].astype(float).tolist())
    ts_arr = np.asarray(ts); ss_arr = np.asarray(ss)
    censor_pts = []
    for t in censor_times:
        idx = int(np.searchsorted(ts_arr, t, side='right') - 1)
        if idx < 0:
            s = 1.0
        else:
            s = float(ss_arr[idx])
        censor_pts.append([round(t / 12, 4), round(s, 4)])
    return ts, ss, censor_pts


def km_at_times(d, times_months):
    """回傳指定時點 (月) 的存活率 list[float|None]."""
    if len(d) == 0:
        return [None] * len(times_months)
    f = KaplanMeierFitter().fit(d.Surv_Months.to_numpy(float),
                                event_observed=d.event.to_numpy(int))
    ts = f.survival_function_.index.to_numpy(float)
    ss = f.survival_function_.iloc[:, 0].to_numpy(float)
    out = []
    for t in times_months:
        if t > ts[-1] and ss[-1] > 0:
            out.append(None)
        else:
            out.append(float(ss[np.searchsorted(ts, t, side='right') - 1]))
    return out


def life_table(d):
    """原分析格式：At risk | Deaths | Censored | Cumulative survival (6 欄含 Months)."""
    if len(d) == 0:
        return []
    events = survival_table_from_events(d.Surv_Months.to_numpy(float),
                                        d.event.to_numpy(int))
    et = events.index.to_numpy(float)
    out, cum = [], 1.0
    for a in range(0, 60, 12):
        b = a + 12
        inside = (et >= a) & ((et <= b) if b == 60 else (et < b))
        n = int(d.Surv_Months.ge(a).sum())
        death = int(events.loc[inside, 'observed'].sum())
        censor = int(events.loc[inside, 'censored'].sum())
        effective = n - censor / 2
        interval = 1 - death / effective if effective > 0 else math.nan
        if n == 0 or (d.Surv_Months.max() < b and cum != 0):
            cum = math.nan
        elif cum == 0:
            pass
        else:
            cum *= interval
        out.append({
            'months': f'{a}–{b}',
            'at_risk': n,
            'deaths': death,
            'censored': censor,
            'cum': None if math.isnan(cum) else round(cum * 100, 1),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', required=True)
    ap.add_argument('--rules', required=True)
    ap.add_argument('--out', default='test/surviva/survival_echarts.html')
    args = ap.parse_args()

    raw = pd.read_excel(args.cases, sheet_name='LF_8', dtype=str)
    raw = raw.loc[raw.select_memo.eq('15_納入統計人數')].copy()
    raw['age'] = pd.to_numeric(raw.age, errors='coerce')
    raw['Surv_Months'] = pd.to_numeric(raw.Surv_Months, errors='coerce')
    raw['event'] = raw.Status_OS.map({'death': 1, 'censor': 0})
    raw = raw.dropna(subset=['age', 'Surv_Months', 'event', 'pri_site', 'didiag'])
    raw = raw[raw.Surv_Months.ge(0)]
    raw['stage'] = raw.fnstage.str.extract(r'^([1-4])', expand=False).map(
        {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'})

    data = {}
    for cancer in CANCERS:
        z = raw[raw.pri_site.eq(cancer)].copy()
        if cancer == 'Pancreas':
            z = z[z.year.astype(int).between(111, 112)]
        elif cancer == 'Cervix':
            z = z[z.year.astype(int).between(110, 112)]
        else:
            z = z[z.year.astype(int).between(108, 112)]
        if len(z) == 0:
            continue
        curves, tables, annual = {}, {}, {}
        for stage in STAGES:
            g = z if stage == 'All' else z[z.stage.eq(stage)]
            ts, ss, censor_pts = km_curve(g)
            curves[stage] = {
                'n': len(g),
                'points': [[round(t / 12, 4), round(s, 4)] for t, s in zip(ts, ss)],
                'censored': censor_pts,
            }
            tables[stage] = life_table(g)
            annual[stage] = {
                'n': len(g),
                'rates': [None if v is None else round(v * 100, 1)
                          for v in km_at_times(g, [12, 24, 36, 48, 60])],
            }
        data[cancer] = {'total': len(z), 'curves': curves,
                        'tables': tables, 'annual': annual}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace('__DATA__', json.dumps(data, ensure_ascii=False))
    out.write_text(html, encoding='utf-8')
    print(f'Wrote {out}  ({len(data)} cancers)')


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<title>存活率 ECharts 獨立測試</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  body { font-family: "Microsoft JhengHei", sans-serif; margin: 20px; background: #f7f9fb; color:#1a202c; }
  h1 { font-size: 20px; margin: 0 0 12px; }
  .bar { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
  select { padding: 6px 10px; font-size: 14px; }
  #chart { width: 100%; height: 520px; background: #fff; border-radius: 8px;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  .note { color: #666; font-size: 12px; margin: 6px 0 14px; }
  .block { margin-top: 18px; background: #fff; border-radius: 8px;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); padding: 12px 16px; }
  .block-title { font-weight: 600; margin-bottom: 8px; color: #2a4365; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid #e2e8f0; padding: 6px 10px; text-align: center; }
  th { background: #edf2f7; }
</style>
</head>
<body>
  <h1>存活率 ECharts 獨立測試</h1>
  <div class="bar">
    <label>癌別：</label>
    <select id="cancer"></select>
    <span id="meta" class="note"></span>
  </div>
  <div class="note">曲線上的「+」記號 = 設限個案 (censored)：該時點仍存活但追蹤結束。</div>
  <div id="chart"></div>

  <div class="block">
    <div class="block-title">年度 Kaplan–Meier 觀察存活率 (%)</div>
    <table id="annual-table"></table>
  </div>

  <div id="life-tables"></div>

<script>
const DATA = __DATA__;
const STAGES = ['All', 'I', 'II', 'III', 'IV'];
const COLORS = {'All':'#2b6cb0','I':'#38a169','II':'#d69e2e','III':'#dd6b20','IV':'#c53030'};

const sel = document.getElementById('cancer');
Object.keys(DATA).forEach(c => {
  const o = document.createElement('option'); o.value = c; o.textContent = c;
  sel.appendChild(o);
});

const chart = echarts.init(document.getElementById('chart'));
window.addEventListener('resize', () => chart.resize());

function buildStepped(points) {
  const out = [];
  for (let i = 0; i < points.length; i++) {
    const [x, y] = points[i];
    if (i > 0) out.push([x, points[i-1][1]]);
    out.push([x, y]);
  }
  return out;
}

function renderCancer(cancer) {
  const d = DATA[cancer];
  document.getElementById('meta').textContent = `總個案數 n = ${d.total}`;

  const activeStages = STAGES.filter(s => d.curves[s] && d.curves[s].points.length);
  const series = [];
  activeStages.forEach(stage => {
    const c = d.curves[stage];
    series.push({
      name: `${stage} (n=${c.n})`,
      type: 'line', step: 'end', showSymbol: false,
      lineStyle: { width: 2, color: COLORS[stage] },
      itemStyle: { color: COLORS[stage] },
      data: buildStepped(c.points),
      emphasis: { focus: 'series' },
      z: 2,
    });
    // 設限「+」記號，與同 stage 曲線同組 (用同名加 _censor 隱藏於圖例)
    if (c.censored && c.censored.length) {
      series.push({
        name: `${stage} (n=${c.n})`,
        type: 'scatter',
        symbol: 'path://M0,-6 L0,6 M-6,0 L6,0',
        symbolSize: 10,
        itemStyle: { color: COLORS[stage], borderColor: COLORS[stage], borderWidth: 1.5 },
        data: c.censored,
        tooltip: { show: false },
        legendHoverLink: false,
        z: 3,
      });
    }
  });

  chart.setOption({
    title: { text: `${cancer} — Kaplan–Meier observed survival`, left: 'center',
             textStyle: { fontSize: 15 } },
    tooltip: { trigger: 'axis',
               valueFormatter: v => (v == null ? '-' : (v*100).toFixed(1) + '%') },
    legend: { bottom: 0, data: activeStages.map(s => `${s} (n=${d.curves[s].n})`) },
    grid: { left: 60, right: 30, top: 50, bottom: 50 },
    xAxis: { type: 'value', name: 'Years since diagnosis', min: 0, max: 5,
             nameLocation: 'middle', nameGap: 28 },
    yAxis: { type: 'value', name: 'Survival', min: 0, max: 1,
             axisLabel: { formatter: v => (v*100).toFixed(0) + '%' } },
    series,
  }, true);

  // 年度 KM 表
  const at = document.getElementById('annual-table');
  at.innerHTML = `
    <thead><tr>
      <th>AJCC Stage</th><th>Cases</th>
      <th>1-yr</th><th>2-yr</th><th>3-yr</th><th>4-yr</th><th>5-yr</th>
    </tr></thead>
    <tbody>${STAGES.map(stage => {
      const a = d.annual[stage];
      if (!a || !a.n) return `<tr><td>${stage}</td><td>0</td>${'<td>—</td>'.repeat(5)}</tr>`;
      return `<tr>
        <td>${stage}</td><td>${a.n}</td>
        ${a.rates.map(r => `<td>${r == null ? 'NA' : r.toFixed(1)}</td>`).join('')}
      </tr>`;
    }).join('')}</tbody>`;

  // 生命表（原格式）
  const host = document.getElementById('life-tables');
  host.innerHTML = '';
  STAGES.forEach(stage => {
    const rows = d.tables[stage];
    if (!rows || !rows.length) return;
    const block = document.createElement('div'); block.className = 'block';
    block.innerHTML = `
      <div class="block-title">12-month actuarial life table — ${stage} (n = ${d.curves[stage].n})</div>
      <table>
        <thead><tr>
          <th>Stage</th><th>Months</th><th>At risk</th>
          <th>Deaths</th><th>Censored</th><th>Cumulative survival</th>
        </tr></thead>
        <tbody>${rows.map(r => `
          <tr>
            <td>${stage}</td><td>${r.months}</td><td>${r.at_risk}</td>
            <td>${r.deaths}</td><td>${r.censored}</td>
            <td>${r.cum == null ? 'NA' : r.cum.toFixed(1) + '%'}</td>
          </tr>`).join('')}
        </tbody>
      </table>`;
    host.appendChild(block);
  });
}

sel.addEventListener('change', e => renderCancer(e.target.value));
sel.value = Object.keys(DATA)[0];
renderCancer(sel.value);
</script>
</body>
</html>
"""


if __name__ == '__main__':
    main()

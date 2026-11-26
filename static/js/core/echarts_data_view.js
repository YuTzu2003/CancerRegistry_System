(function (global) {
  function valueOf(point) {
    return point && typeof point === 'object' && !Array.isArray(point) ? point.value : point;
  }

  function axes(option, name) {
    const axis = option[name];
    return Array.isArray(axis) ? axis : axis ? [axis] : [];
  }

  function addTable(host, title, headings, rows) {
    if (title) {
      const heading = document.createElement('h5');
      heading.textContent = title;
      heading.style.margin = '16px 0 8px';
      host.appendChild(heading);
    }
    const table = document.createElement('table');
    table.style.cssText = 'border-collapse:collapse;width:100%;margin-bottom:16px;';
    const header = table.createTHead().insertRow();
    headings.forEach(label => {
      const cell = document.createElement('th');
      cell.textContent = label;
      cell.style.cssText = 'border:1px solid #888;padding:6px 10px;text-align:left;';
      header.appendChild(cell);
    });
    const body = table.createTBody();
    rows.forEach(values => {
      const row = body.insertRow();
      values.forEach(value => {
        const cell = row.insertCell();
        cell.textContent = value == null ? '' : String(value);
        cell.style.cssText = 'border:1px solid #888;padding:6px 10px;';
      });
    });
    host.appendChild(table);
  }

  function optionToContent(option) {
    const host = document.createElement('div');
    host.style.cssText = 'height:100%;overflow:auto;padding:0 16px;box-sizing:border-box;';
    const english = global.DashboardI18n?.getLanguage() === 'en';
    const categoryAxis = [...axes(option, 'xAxis'), ...axes(option, 'yAxis')]
      .find(axis => axis.type === 'category' && Array.isArray(axis.data));
    const series = (option.series || []).filter(item =>
      Array.isArray(item.data) && item.type !== 'custom' && !String(item.name || '').startsWith('__'));

    if (categoryAxis) {
      const headings = [categoryAxis.name || (english ? 'Category' : '分類')];
      const hasCount = series.map(item => item.data.some(point =>
        point && typeof point === 'object' && point.count != null));
      series.forEach((item, index) => {
        headings.push(item.name || (english ? `Series ${index + 1}` : `系列 ${index + 1}`));
        if (hasCount[index]) headings.push(english ? 'Count' : '人數');
      });
      const rows = categoryAxis.data.map((category, index) => {
        const values = [valueOf(category)];
        series.forEach((item, seriesIndex) => {
          const point = item.data[index];
          values.push(valueOf(point));
          if (hasCount[seriesIndex]) values.push(point?.count);
        });
        return values;
      });
      addTable(host, '', headings, rows);
    } else {
      const xName = axes(option, 'xAxis')[0]?.name || (english ? 'X' : '橫軸');
      const yName = axes(option, 'yAxis')[0]?.name || (english ? 'Y' : '縱軸');
      series.forEach((item, index) => {
        const paired = item.data.some(point => Array.isArray(valueOf(point)));
        const rows = item.data.map((point, pointIndex) => {
          const value = valueOf(point);
          return paired ? [value?.[0], value?.[1]] : [pointIndex + 1, value];
        });
        addTable(host, item.name || (english ? `Series ${index + 1}` : `系列 ${index + 1}`),
          [paired ? xName : (english ? 'No.' : '序號'), paired ? yName : (english ? 'Value' : '數值')], rows);
      });
    }
    return host;
  }

  global.EChartsDataView = { viewOnly: { optionToContent } };
})(window);

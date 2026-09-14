const dashboardCancerNameTranslationsData = document.getElementById('dashboardCancerNameTranslationsData');
  try {
    window.dashboardCancerNameTranslations = JSON.parse(dashboardCancerNameTranslationsData?.textContent || '{}');
  } catch (error) {
    console.error('癌別翻譯資料解析失敗：', error);
    window.dashboardCancerNameTranslations = {};
  }

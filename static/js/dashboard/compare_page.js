try {
    window.dashboardCancerNameTranslations = JSON.parse(document.getElementById('dashboardCancerNameTranslationsData')?.textContent || '{}');
  } catch (error) {
    window.dashboardCancerNameTranslations = {};
  }

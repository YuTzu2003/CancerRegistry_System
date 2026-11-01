"""Browser regression for unsaved indicator edits; all API calls are mocked."""
import importlib.util
import json
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Playwright is unavailable')
class IndicatorMaintenanceBrowserTests(unittest.TestCase):
    def test_version_history_can_preview_without_restore_control(self):
        from playwright.sync_api import Error, sync_playwright

        root = Path(__file__).resolve().parents[1]
        markup = '''<html><body><div id="definitionReview" data-can-approve="false"
          data-cancers='[{"key":"Ovary","name":"卵巢癌"}]'></div>
          <div id="reviewTimeline"></div><div id="reviewStatus"></div><div id="reviewCount"></div>
          <select id="reviewUser"><option value="">所有操作者</option></select>
          <input id="reviewDate" type="date"><button id="reviewClear" hidden>清除篩選</button></body></html>'''
        version = {'id': '1', 'name': '測試版本', 'status': 'PUBLISHED', 'complete': True,
                   'created_by': '管理員', 'created_by_key': 'user', 'created_at': '2026-01-01T00:00:00Z', 'cancers': ['Ovary']}
        details = {'ok': True, 'cancer_key': 'Ovary', 'descriptions': [{'id': 1, 'name': '測試指標',
                   'numerator_definition': '分子', 'denominator_definition': '分母'}], 'conditions': [],
                   'rule_trees': {'1': {'numerator': {'op': 'equals'}, 'denominator': {'op': 'equals'}}}, 'field_labels': {}}
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True, channel='chrome')
            except Error:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except Error:
                    self.skipTest('A Playwright-compatible browser is unavailable')
            try:
                page = browser.new_page()
                page.set_content(markup)
                page.evaluate('''([version, details]) => {
                  window.fetch = async url => ({ok:true, json:async()=>url.includes('/cancers/') ? details : {ok:true,versions:[version]}});
                  window.Swal = {fire:async options => { window.__preview = options.html; }};
                  window.describeIndicatorRule = () => '測試條件';
                }''', [version, details])
                page.add_script_tag(path=str(root / 'static/js/indicators/indicator_definition_review.js'))
                page.locator('[data-preview-id="1"]').wait_for()
                self.assertEqual(page.locator('[data-restore-id]').count(), 0)
                page.locator('[data-preview-id="1"]').click()
                page.wait_for_function('window.__preview !== undefined')
                self.assertIn('測試指標', page.evaluate('window.__preview'))
            finally:
                browser.close()

    def test_existing_edits_survive_new_indicator_and_cancer_switch(self):
        from playwright.sync_api import Error, sync_playwright

        root = Path(__file__).resolve().parents[1]
        markup = '''<!doctype html><html><body>
          <a id="backToIndicators" href="/indicators"></a>
          <div id="definitionManager" data-can-manage="true" data-can-approve="false">
          <select id="definitionCancer"><option value="Oral_Cavity">口腔癌</option><option value="Ovary">卵巢癌</option></select>
          <select id="definitionVersion"></select><button id="startDefinitionEdit"><span id="startDefinitionEditLabel"></span></button>
          <button id="reviseDefinitionVersion"><span id="reviseDefinitionVersionLabel"></span></button>
          <button id="deleteDefinitionVersion"></button><button id="definitionHistory"></button>
          <span id="definitionStatus"></span><span id="definitionVersionState"></span>
          <div id="definitionEditSettings"></div><p id="definitionRevisionHint"></p><p id="definitionDraftStatus"></p>
          <input id="definitionYear"><textarea id="definitionVersionDescription"></textarea><textarea id="definitionChangeReason"></textarea>
          <button id="cancelDefinitionEdit"></button><div id="definitionContents"></div>
          <div id="definitionEditActions"><button id="saveDefinitionVersion"></button></div></div>
          </body></html>'''
        version = {'id': 'default', 'name': '基準', 'status': 'PUBLISHED', 'cancers': ['Oral_Cavity', 'Ovary']}
        rules = {'1': {'numerator': {'op': 'equals', 'field': '8.3', 'value': 0},
                       'denominator': {'op': 'between', 'field': '8.5', 'min': 1, 'max': 5}},
                 '2': {'numerator': {'op': 'equals', 'field': '8.3', 'value': 1},
                       'denominator': {'op': 'between', 'field': '8.5', 'min': 1, 'max': 5}}}
        details = {'ok': True, 'included': True, 'version': version, 'conditions': [], 'rule_trees': rules,
                   'field_labels': {'8.3': '癌症部位特定因子 3', '8.5': '癌症部位特定因子 5'},
                   'descriptions': [{'id': n, 'name': f'原指標 {n}', 'numerator_definition': '原分子',
                                     'denominator_definition': '原分母'} for n in (1, 2)]}
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True, channel='chrome')
            except Error:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except Error:
                    self.skipTest('A Playwright-compatible browser is unavailable')
            try:
                page = browser.new_page()
                page.route('http://indicator.test/**', lambda route: route.fulfill(status=200, content_type='text/html', body=markup))
                page.goto('http://indicator.test/indicators/definitions')
                page.evaluate('''([version, details]) => {
                    window.__details = details;
                    window.fetch = async (url, options = {}) => {
                      if (options.method === 'POST') { window.__submitted = JSON.parse(options.body); return {ok:false, json:async()=>({ok:false,error:'此版本已被其他人修改，請重新整理後再編輯。'})}; }
                      if (url.includes('/cancers/')) return {ok:true, json:async()=>({...window.__details, cancer_key:decodeURIComponent(url.split('/').pop())})};
                      return {ok:true, json:async()=>({ok:true,versions:[version]})};
                    };
                    window.Swal = {fire:async()=>({isConfirmed:true})};
                    window.utils = {confirm:async()=>({isConfirmed:true})};
                    window.openIndicatorRuleEditor = async tree => ({...tree, value:2});
                    window.describeIndicatorRule = () => '測試條件';
                }''', [version, details])
                page.add_script_tag(path=str(root / 'static/js/indicators/indicator_definitions.js'))
                page.locator('#startDefinitionEdit').wait_for(state='visible')
                page.wait_for_function("!document.getElementById('startDefinitionEdit').disabled")
                page.click('#startDefinitionEdit')
                page.fill('#definitionYear', '2027')
                page.locator('[data-rule-indicator="1"] summary').click()
                page.locator('[data-rule-indicator="1"] [data-description="name"]').fill('已修改名稱')
                page.locator('[data-rule-indicator="1"] [data-edit-rule-tree="numerator"]').click()
                page.wait_for_function("JSON.parse(document.querySelector('[data-rule-indicator=\"1\"] [data-rule-tree=\"numerator\"]').value).value === 2")
                page.locator('[data-rule-indicator="2"] summary').click()
                page.locator('[data-rule-indicator="2"] [data-remove-indicator]').check()
                page.click('[data-add-new-indicator]')
                self.assertEqual(page.locator('[data-rule-indicator="1"] [data-description="name"]').input_value(), '已修改名稱')
                self.assertTrue(page.locator('[data-rule-indicator="2"] [data-remove-indicator]').is_checked())
                self.assertEqual(json.loads(page.locator('[data-rule-indicator="1"] [data-rule-tree="numerator"]').input_value())['value'], 2)
                page.fill('[data-new-name]', '新增指標')
                page.fill('[data-new-numerator-description]', '新分子')
                page.fill('[data-new-denominator-description]', '新分母')
                page.locator('[data-new-condition="numerator"] [data-new-value]').fill('1')
                page.locator('[data-new-condition="denominator"] [data-new-value]').fill('1')
                page.locator('[data-add-new-condition][data-section="denominator"]').click()
                self.assertEqual(page.locator('[data-rule-indicator="1"] [data-description="name"]').input_value(), '已修改名稱')
                self.assertEqual(page.locator('[data-new-name]').input_value(), '新增指標')
                page.locator('[data-remove-new-condition][data-section="denominator"]').last.click()
                page.select_option('#definitionCancer', 'Ovary')
                page.wait_for_function("document.querySelector('#definitionCancer').value === 'Ovary' && !document.querySelector('#definitionCancer').disabled")
                page.select_option('#definitionCancer', 'Oral_Cavity')
                page.wait_for_function("document.querySelector('#definitionCancer').value === 'Oral_Cavity' && !document.querySelector('#definitionCancer').disabled")
                self.assertEqual(page.locator('[data-rule-indicator="1"] [data-description="name"]').input_value(), '已修改名稱')
                self.assertEqual(page.locator('[data-new-name]').input_value(), '新增指標')
                page.click('#saveDefinitionVersion')
                page.wait_for_function('window.__submitted !== undefined')
                submitted = page.evaluate('window.__submitted.cancer_edits.Oral_Cavity')
                self.assertEqual(submitted['descriptions'][0]['name'], '已修改名稱')
                self.assertEqual(submitted['rule_trees']['1']['numerator']['value'], 2)
                self.assertEqual(submitted['removed_indicators'], [2])
                self.assertEqual(submitted['new_indicators'][0]['name'], '新增指標')
                page.wait_for_function("document.querySelector('#definitionStatus').textContent.includes('已被其他人修改')")
                self.assertEqual(page.locator('[data-rule-indicator="1"] [data-description="name"]').input_value(), '已修改名稱')
                self.assertEqual(page.locator('[data-new-name]').input_value(), '新增指標')
            finally:
                browser.close()

    def test_rule_editor_selects_existing_and_unknown_fields(self):
        from playwright.sync_api import Error, sync_playwright
        from modules.blueprint.indicators.indicator_definitions import RULE_FIELD_LABELS

        root = Path(__file__).resolve().parents[1]
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True, channel='chrome')
            except Error:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except Error:
                    self.skipTest('A Playwright-compatible browser is unavailable')
            try:
                page = browser.new_page()
                page.set_content('<html><body></body></html>')
                page.add_script_tag(path=str(root / 'static/vendor/sweetalert2/sweetalert2.all.min.js'))
                page.add_script_tag(path=str(root / 'static/js/indicators/indicator_rule_editor.js'))
                page.evaluate('''fields => {
                    window.openIndicatorRuleEditor({op:'equals', field:'8.3', value:0}, fields)
                      .then(result => { window.__rule = result; });
                }''', RULE_FIELD_LABELS)
                self.assertEqual(page.locator('[data-rule-key="field"]').input_value(), '8.3')
                self.assertIn('癌症部位特定因子 3', page.locator('[data-rule-key="field"] option:checked').inner_text())
                page.locator('[data-rule-key="value"]').fill('10')
                page.locator('.swal2-confirm').click()
                page.wait_for_function('window.__rule !== undefined')
                self.assertEqual(page.evaluate('window.__rule'), {'op': 'equals', 'field': '8.3', 'value': 10})
                page.evaluate('''fields => {
                    window.openIndicatorRuleEditor({op:'equals', field:'????????', value:1}, fields)
                      .then(result => { window.__unknown = result; });
                }''', RULE_FIELD_LABELS)
                self.assertEqual(page.locator('[data-rule-key="field"]').input_value(), '????????')
                self.assertIn('原設定欄位待確認', page.locator('[data-rule-key="field"] option:checked').inner_text())
                page.locator('.swal2-cancel').click()
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()

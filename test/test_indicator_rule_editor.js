const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const listeners = {};
const host = { innerHTML: '', addEventListener: (type, callback) => { listeners[type] = callback; } };
let change;
const context = {
  window: {}, document: { getElementById: () => host },
  Swal: { fire: async options => {
    options.didOpen();
    assert(host.innerHTML.includes('條件類型'));
    change();
    return { isConfirmed: true, value: options.preConfirm() };
  }, showValidationMessage: message => { throw new Error(message); } },
  JSON, Object, Array, Number, String,
};
vm.runInNewContext(fs.readFileSync('static/js/indicators/indicator_rule_editor.js', 'utf8'), context);

(async () => {
  const fields = {'4.1.2': '手術日期', '4.2.1.3': '放療日期'};
  const dateRule = {op:'earliest_after_within', reference_field:'4.1.2', candidate_fields:['4.2.1.3'], min_days:1, max_days:42};
  change = () => listeners.change({target:{dataset:{path:'[]', ruleKey:'max_days'}, value:'60', matches:() => false}});
  const revised = await context.window.openIndicatorRuleEditor(dateRule, fields);
  assert.strictEqual(revised.max_days, 60);
  assert.strictEqual(dateRule.max_days, 42);

  const group = {op:'all', rules:[{op:'valid_date', field:'4.1.2'}, {op:'valid_date', field:'4.2.1.3'}]};
  change = () => listeners.change({target:{dataset:{path:'[]'}, value:'any', matches:() => true}});
  const switched = await context.window.openIndicatorRuleEditor(group, fields);
  assert.strictEqual(switched.op, 'any');
  assert.strictEqual(switched.rules.length, 2);
  change = () => {
    assert(host.innerHTML.includes('value="????????" selected'));
    assert(host.innerHTML.includes('原設定欄位待確認'));
  };
  const unknown = await context.window.openIndicatorRuleEditor({op:'equals', field:'????????', value:1}, fields);
  assert.strictEqual(unknown.field, '????????');
  console.log('Rule editor interactions passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });

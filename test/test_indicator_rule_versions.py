import json
import unittest
from unittest.mock import Mock, patch

import pandas as pd
from flask import Flask, session

from modules.blueprint.indicators.catalog import CANCER_SPECS
from modules.blueprint.indicators.analysis import build_indicators_export_frame, run_indicators_analysis
from modules.blueprint.indicators.definition_versions import decode_definition, default_definition
from modules.blueprint.indicators.rule_versions import apply_changes, default_rules, editable_conditions, load_version, next_revision_name, validate_rule_tree, build_user_indicator
from modules.blueprint.indicators.rule import evaluate_rule
from modules.blueprint.indicators.indicator_definitions import RULE_FIELD_LABELS, _calculator_for
import modules.services.indicators as indicator_service


class IndicatorRuleVersionTests(unittest.TestCase):
    def test_registered_rule_fields_can_be_edited_and_used_by_code_or_name(self):
        for cancer, number in [('Ovary', 3), ('Lung', 1)]:
            original = default_rules(cancer)[number]['numerator']
            edited = dict(original)
            key = 'value' if 'value' in edited else 'min'
            edited[key] += 1
            self.assertEqual(validate_rule_tree(edited, original), edited)
            self.assertIn(original['field'], RULE_FIELD_LABELS)
        rule = {'denominator': {'op': 'equals', 'field': '8.3', 'value': 10},
                'numerator': {'op': 'between', 'field': '8.5', 'min': 1, 'max': 5}}
        for frame in (pd.DataFrame({'8.3': [10, 11], '8.5': [3, 3]}),
                      pd.DataFrame({'癌症部位特定因子 3': [10, 11], '癌症部位特定因子 5': [3, 3]})):
            masks = _calculator_for(rule)(frame)
            self.assertEqual(masks['denominator_mask'].tolist(), [True, False])
            self.assertEqual(masks['numerator_mask'].tolist(), [True, False])

    def test_unknown_rule_fields_are_not_silently_accepted(self):
        original = {'op': 'equals', 'field': '????????', 'value': 1}
        self.assertEqual(validate_rule_tree(original, original), original)
        with self.assertRaises(ValueError):
            validate_rule_tree(dict(original, value=2), original)

    def test_date_rule_changes_and_code_group_evaluate_as_configured(self):
        original = default_rules('Oral_Cavity')[1]['numerator']
        changed = dict(original, max_days=60)
        changed = validate_rule_tree(changed, original)
        sample = {'4.1.2': '20250101', '4.2.1.3': '20250220', '4.3.4': '20250301'}
        self.assertFalse(evaluate_rule(sample, original))
        self.assertTrue(evaluate_rule(sample, changed))
        group = validate_rule_tree({'op': 'any', 'rules': [
            {'op': 'text_in', 'field': '4.1.5', 'values': ['0', 'C']},
            {'op': 'date_after', 'start_field': '4.1.2', 'end_field': '4.2.1.3'},
        ]})
        self.assertTrue(evaluate_rule(sample, group))

    def test_new_indicator_can_use_date_and_or_rules_and_rejects_invalid_input(self):
        group = {'op': 'all', 'rules': [
            {'op': 'valid_date', 'field': '4.1.2'},
            {'op': 'any', 'rules': [
                {'op': 'date_after', 'start_field': '4.1.2', 'end_field': '4.2.1.3'},
                {'op': 'date_after', 'start_field': '4.1.2', 'end_field': '4.3.4'},
            ]},
        ]}
        item = {'name': 'Date indicator', 'type': 'positive', 'numerator': group, 'denominator': group}
        self.assertEqual(build_user_indicator(item, 1)['numerator'], group)
        with self.assertRaises(ValueError):
            validate_rule_tree({'op': 'date_interval', 'start_field': '4.1.2', 'end_field': '4.2.1.3', 'min_days': 42, 'max_days': 1})
        with self.assertRaises(ValueError):
            validate_rule_tree({'op': 'valid_date', 'field': 'unknown'})

    def test_special_existing_rule_operations_are_editable(self):
        field_labels = {
            '2.5': '診斷日期', '3.13': '病理期別', '3.21': '優先期別',
            '4.1.2': '手術日期', '4.2.2.2.2': '放療劑量', '4.2.2.2.3': '放療分次',
        }
        special_rules = [
            {'op': 'date_year_between', 'field': '2.5', 'min': 2024, 'max': 2026},
            {'op': 'stage_first_char_in', 'field': '3.13', 'values': ['2', '3']},
            {'op': 'stage_matches', 'field': '3.13', 'pattern': r'[1-4][A-C]?'},
            {'op': 'preferred_stage_in', 'preferred_field': '3.21', 'fallback_field': '3.13',
             'invalid_values': ['', '9999'], 'values': ['2', '3A']},
            {'op': 'bed_at_least', 'courses': [{'dose_field': '4.2.2.2.2', 'fractions_field': '4.2.2.2.3'}],
             'value': 150},
        ]
        from modules.blueprint.indicators import indicator_definitions
        original_labels = indicator_definitions.RULE_FIELD_LABELS
        indicator_definitions.RULE_FIELD_LABELS = field_labels
        try:
            for rule in special_rules:
                with self.subTest(operation=rule['op']):
                    self.assertEqual(validate_rule_tree(rule), rule)
        finally:
            indicator_definitions.RULE_FIELD_LABELS = original_labels

    def test_all_special_rule_operations_are_accepted_by_the_version_validator(self):
        from modules.blueprint.indicators import indicator_definitions

        labels = {key: key for key in (
            '2.3', '2.3.1', '2.3.2', '3.13', '8.3',
        )}
        operations = [
            {'op': 'text_equals', 'field': '8.3', 'value': '000'},
            {'op': 'text_not_equals', 'field': '8.3', 'value': '888'},
            {'op': 'text_starts_with', 'field': '8.3', 'values': ['A', 'B']},
            {'op': 'text_in_without_prefix', 'field': '3.13', 'prefix': 'c', 'values': ['1', '2A']},
            {'op': 'zero_fill_text_in', 'field': '8.3', 'width': 2, 'values': ['01', '10']},
            {'op': 'all_fields_not_in', 'fields': ['2.3', '2.3.1', '2.3.2'], 'values': ['20', '21']},
            {'op': 'concatenated_text_in', 'fields': ['2.3', '2.3.1', '2.3.2'], 'values': ['111']},
            {'op': 'first_char_in', 'field': '3.13', 'values': ['1', '2']},
        ]
        original_labels = indicator_definitions.RULE_FIELD_LABELS
        indicator_definitions.RULE_FIELD_LABELS = labels
        try:
            for rule in operations:
                with self.subTest(operation=rule['op']):
                    self.assertEqual(validate_rule_tree(rule), rule)
        finally:
            indicator_definitions.RULE_FIELD_LABELS = original_labels

    def test_revision_names_follow_the_same_family_and_fit_the_database(self):
        self.assertEqual(next_revision_name({'id': '1', 'name': 'Annual'}, []), 'Annual・修訂 1')
        self.assertEqual(next_revision_name({'id': '2', 'name': 'Annual・修訂 1'},
                                            ['Annual', 'Annual・修訂 1', 'Annual・修訂 3']), 'Annual・修訂 4')
        name = next_revision_name({'id': '123', 'name': 'A' * 100}, [])
        self.assertLessEqual(len(name), 100)
        next_name = next_revision_name({'id': '124', 'name': name}, [name])
        self.assertEqual(next_name.rsplit(' ', 1)[1], '2')
        self.assertLessEqual(len(next_name), 100)

    def test_all_cancers_keep_their_rules_when_saved_without_changes(self):
        self.assertEqual(len(CANCER_SPECS), 13)
        for cancer_key, spec in CANCER_SPECS.items():
            with self.subTest(cancer=cancer_key):
                rules = default_rules(cancer_key)
                self.assertEqual(apply_changes(rules, editable_conditions(rules)), spec.rules)
                self.assertIsNot(rules, spec.rules)

    def test_initial_definition_snapshot_matches_python_rules_and_analysis_output(self):
        """The first database-ready snapshot must behave exactly like Python defaults."""
        snapshot = decode_definition(json.dumps(default_definition(), ensure_ascii=False))
        self.assertEqual(snapshot, {key: default_rules(key) for key in CANCER_SPECS})

        frame = pd.DataFrame({'record_id': ['case-1'], '2.5': ['20250101'], '4.1.4': ['50']})
        with patch('modules.blueprint.indicators.analysis.get_indicator_metadata', return_value=[]), \
             patch('modules.blueprint.indicators.analysis.cancer_case_mask', return_value=pd.Series([True])), \
             patch('modules.blueprint.indicators.analysis.apply_global_indicators_exclusions',
                   side_effect=lambda data, **_: (data, data, {})):
            for cancer_key in CANCER_SPECS:
                with self.subTest(cancer=cancer_key):
                    python_result = run_indicators_analysis(
                        frame, [cancer_key], 2025, 2025,
                        rules_by_cancer={cancer_key: default_rules(cancer_key)},
                    )
                    snapshot_result = run_indicators_analysis(
                        frame, [cancer_key], 2025, 2025,
                        rules_by_cancer={cancer_key: snapshot[cancer_key]},
                    )
                    self.assertEqual(snapshot_result, python_result)

    def test_analysis_run_snapshot_preserves_rules_results_and_target_thresholds(self):
        app = Flask(__name__)
        app.secret_key = 'test-key'
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = (42,)
        rules = {'Oral_Cavity': default_rules('Oral_Cavity')}
        result = {'reports': [{
            'cancer_key': 'Oral_Cavity', 'input_count': 5, 'included_count': 4,
            'global_exclusions': {'excluded_count': 1},
            'indicators': [{'id': 1, 'name': 'Test', 'numerator': 2, 'denominator': 4,
                            'percentage': 50.0, 'numerator_definition': 'N',
                            'denominator_definition': 'D', 'target_value': 60,
                            'target_operator': '>=', 'direction': 'positive'}],
        }]}
        with app.test_request_context('/'):
            session['userid'] = 'test-user'
            with patch.object(indicator_service, 'get_conn', return_value=connection):
                run_id = indicator_service._record_indicator_analysis_run(
                    cancers=['Oral_Cavity'], year_start=2025, year_end=2025,
                    rules_by_cancer=rules,
                    versions={'Oral_Cavity': {'id': 'default', 'name': '原始指標定義'}},
                    result=result,
                )
        self.assertEqual(run_id, 42)
        params = cursor.execute.call_args.args[1]
        self.assertEqual(params[:6], ('test-user', 2025, 2025, '["Oral_Cavity"]', None, '原始指標定義'))
        self.assertEqual(json.loads(params[6]), json.loads(json.dumps(rules)))
        persisted_result = json.loads(params[7])
        self.assertNotIn('source_rows', persisted_result)
        saved_indicator = persisted_result['reports'][0]['indicators'][0]
        self.assertEqual(saved_indicator['denominator'], 4)
        self.assertEqual(saved_indicator['target_value'], 60)
        self.assertEqual(saved_indicator['target_operator'], '>=')
        self.assertFalse(saved_indicator['target_met'])
        self.assertTrue(indicator_service._indicator_target_met(
            {'target_value': 50, 'percentage': 50, 'direction': 'negative'}
        ))
        connection.commit.assert_called_once()
        connection.close.assert_called_once()

    def test_version_lookup_is_scoped_to_cancer(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = None
        with self.assertRaises(ValueError):
            load_version('Breast', '7', lambda: connection)
        self.assertEqual(cursor.execute.call_args.args[1], ('Breast', 7))
        connection.close.assert_called_once()

    def test_default_version_does_not_query_database(self):
        factory = Mock(side_effect=AssertionError('Default should not use the database'))
        rules, version = load_version('Lung', 'default', factory)
        self.assertEqual(rules, CANCER_SPECS['Lung'].rules)
        self.assertEqual(version['id'], 'default')

    def test_loaded_snapshot_keeps_its_own_name_and_rules(self):
        connection = Mock()
        rules = default_rules('Breast')
        connection.cursor.return_value.fetchone.return_value = ('Test version', json.dumps(rules))
        loaded, version = load_version('Breast', '9', lambda: connection)
        self.assertEqual(loaded, rules)
        self.assertEqual(version, {'id': '9', 'name': 'Test version'})

    def test_nested_not_condition_can_be_edited_without_changing_its_parent(self):
        rules = {1: {'denominator': {'op': 'not', 'rule': {'op': 'between', 'field': 'value', 'min': 1, 'max': 5}},
                     'numerator': {'op': 'equals', 'field': 'value', 'value': 9}}}
        condition = editable_conditions(rules)[0]
        self.assertEqual(condition['path'], ['rule'])
        edited = apply_changes(rules, [{**condition, 'max': 7}])
        self.assertEqual(edited[1]['denominator']['op'], 'not')
        self.assertEqual(edited[1]['denominator']['rule']['max'], 7)
        self.assertEqual(rules[1]['denominator']['rule']['max'], 5)

    def test_analysis_and_excel_apply_each_cancers_selected_rules(self):
        frame = pd.DataFrame({'record_id': ['o1', 'o2', 'b1', 'b2'],
                              'cancer': ['Oral_Cavity', 'Oral_Cavity', 'Breast', 'Breast'],
                              '2.5': ['20250101'] * 4, '4.1.4': ['35', '40', '35', '40']})
        def rules(minimum):
            return {1: {'name': 'Test', 'type': 'positive',
                        'denominator': {'op': 'between', 'field': '4.1.4', 'min': minimum, 'max': 90},
                        'numerator': {'op': 'equals', 'field': '4.1.4', 'value': 40}}}
        selected = {'Oral_Cavity': rules(40), 'Breast': rules(30)}
        with patch('modules.blueprint.indicators.analysis.get_indicator_metadata', return_value=[]), \
             patch('modules.blueprint.indicators.analysis.cancer_case_mask', side_effect=lambda data, cancer: data['cancer'].eq(cancer)), \
             patch('modules.blueprint.indicators.analysis.apply_global_indicators_exclusions', side_effect=lambda data, **_: (data, data, {})):
            result = run_indicators_analysis(frame, list(selected), 2025, 2025, rules_by_cancer=selected)
            exported = build_indicators_export_frame(frame, list(selected), 2025, 2025, rules_by_cancer=selected)
        self.assertEqual([report['indicators'][0]['denominator'] for report in result['reports']], [1, 2])
        oral_column, breast_column = exported.columns[-3], exported.columns[-1]
        self.assertEqual(exported[oral_column].tolist(), ['', 'V', '', ''])
        self.assertEqual(exported[breast_column].tolist(), ['', '', 'V', 'V'])

    def test_removed_indicator_is_absent_from_analysis_and_export(self):
        frame = pd.DataFrame({'2.5': ['20250101'], '4.1.4': ['40']})
        rules = default_rules('Oral_Cavity')
        removed = next(iter(rules))
        del rules[removed]
        metadata = [{'id': removed, 'numerator_definition': '', 'denominator_definition': ''}]
        with patch('modules.blueprint.indicators.analysis.get_indicator_metadata', return_value=metadata), \
             patch('modules.blueprint.indicators.analysis.cancer_case_mask', return_value=pd.Series([True])), \
             patch('modules.blueprint.indicators.analysis.apply_global_indicators_exclusions', side_effect=lambda data, **_: (data, data, {})):
            result = run_indicators_analysis(frame, ['Oral_Cavity'], 2025, 2025, rules_by_cancer={'Oral_Cavity': rules})
            exported = build_indicators_export_frame(frame, ['Oral_Cavity'], 2025, 2025, rules_by_cancer={'Oral_Cavity': rules})
        self.assertNotIn(removed, [item['id'] for item in result['reports'][0]['indicators']])
        self.assertNotIn(f'Oral_Cavity{removed}-分子', exported.columns)


if __name__ == '__main__':
    unittest.main()

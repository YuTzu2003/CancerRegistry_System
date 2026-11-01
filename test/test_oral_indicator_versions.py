import json
import unittest

from modules.blueprint.indicators.oral_rule_versions import (
    apply_changes, decode_rules, default_rules, editable_conditions,
)
from modules.blueprint.indicators.rule import evaluate_rule


class OralIndicatorVersionTests(unittest.TestCase):
    def setUp(self):
        self.rules = default_rules()
        self.condition = next(item for item in editable_conditions(self.rules)
                              if item['indicator'] == 1 and item['section'] == 'denominator'
                              and item['field'] == '4.1.4')

    def test_new_version_keeps_original_and_includes_range_boundaries(self):
        edited = apply_changes(self.rules, [{**self.condition, 'min': 40, 'max': 90}])
        original = self.rules[1]['denominator']['rules'][0]
        updated = edited[1]['denominator']['rules'][0]
        self.assertTrue(evaluate_rule({'4.1.4': 35}, original))
        self.assertFalse(evaluate_rule({'4.1.4': 35}, updated))
        self.assertTrue(evaluate_rule({'4.1.4': 40}, updated))
        self.assertTrue(evaluate_rule({'4.1.4': 90}, updated))
        self.assertEqual(self.rules[1]['denominator']['rules'][1:], edited[1]['denominator']['rules'][1:])
        self.assertEqual(decode_rules(json.dumps(edited)), edited)

    def test_invalid_range_or_condition_is_rejected(self):
        for change in ({**self.condition, 'min': 91, 'max': 90},
                       {**self.condition, 'path': [999]},
                       {**self.condition, 'op': 'unknown'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                apply_changes(self.rules, [change])

    def test_strict_and_inclusive_less_than(self):
        for operator, expected in [('less_than', (True, False, False)),
                                   ('less_than_or_equal', (True, True, False))]:
            for value, result in zip((39, 40, 41), expected):
                with self.subTest(operator=operator, value=value):
                    self.assertIs(evaluate_rule({'4.1.4': value},
                                                {'op': operator, 'field': '4.1.4', 'value': 40}), result)


if __name__ == '__main__':
    unittest.main()

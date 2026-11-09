from copy import deepcopy
import unittest

from modules.blueprint.indicators import definition_excel


class IndicatorDefinitionExcelTests(unittest.TestCase):
    def setUp(self):
        self.original_specs = definition_excel.CANCER_SPECS
        definition_excel.CANCER_SPECS = {"Demo": object()}
        self.definition = {
            "Demo": {
                1: {
                    "type": "positive", "name": "原始指標", "selection_reason": "理由",
                    "numerator_definition": "分子定義", "denominator_definition": "分母定義", "notes": "備註",
                    "numerator": {"op": "equals", "field": "8.3", "value": 1},
                    "denominator": {"op": "between", "field": "4.1.4", "min": 20, "max": 80},
                }
            }
        }

    def tearDown(self):
        definition_excel.CANCER_SPECS = self.original_specs

    def test_template_round_trip_preserves_rules_and_imports_text(self):
        stream = definition_excel.build_definition_workbook(
            deepcopy(self.definition), version_name="測試版", version_description="測試"
        )
        from openpyxl import load_workbook
        workbook = load_workbook(stream)
        self.assertEqual(workbook.sheetnames[0], definition_excel.INFO_SHEET)
        sheet = workbook[definition_excel.DISPLAY_SHEET]
        self.assertEqual(
            [cell.value for cell in sheet[1]],
            list(definition_excel.DISPLAY_HEADERS),
        )
        self.assertEqual(sheet.cell(2, 9).value, "8.3")
        self.assertEqual(sheet.cell(2, 10).value, "4.1.4")
        sheet.cell(2, 5).value = "Excel 更新後指標"
        output = __import__('io').BytesIO()
        workbook.save(output)
        output.seek(0)

        imported = definition_excel.read_definition_workbook(output, self.definition)

        self.assertEqual(imported["Demo"][1]["name"], "Excel 更新後指標")
        self.assertEqual(imported["Demo"][1]["numerator"], self.definition["Demo"][1]["numerator"])
        self.assertEqual(imported["Demo"][1]["denominator"], self.definition["Demo"][1]["denominator"])

    def test_template_requires_machine_rule_sheet(self):
        stream = definition_excel.build_definition_workbook(deepcopy(self.definition), version_name="測試版")
        from openpyxl import load_workbook
        workbook = load_workbook(stream)
        del workbook[definition_excel.RULE_SHEET]
        output = __import__('io').BytesIO()
        workbook.save(output)
        output.seek(0)

        with self.assertRaisesRegex(ValueError, "系統計算規則"):
            definition_excel.read_definition_workbook(output, self.definition)


if __name__ == '__main__':
    unittest.main()

from pathlib import Path
import unittest

from jinja2 import Environment, FileSystemLoader


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "modules" / "blueprint" / "dashboard" / "templates"


class ReportTaskPanelTests(unittest.TestCase):
    def setUp(self):
        self.template = Environment(loader=FileSystemLoader(TEMPLATE_DIR)).get_template("report_task_panel.html")

    def test_annual_report_panel_uses_annual_record_title(self):
        rendered = self.template.render(llm_task_type="chart")
        self.assertIn("年報紀錄", rendered)
        self.assertNotIn("比較紀錄", rendered)

    def test_comparison_panel_uses_comparison_record_title(self):
        rendered = self.template.render(llm_task_type="comparison_report")
        self.assertIn("比較紀錄", rendered)
        self.assertNotIn("年報紀錄", rendered)


if __name__ == "__main__":
    unittest.main()

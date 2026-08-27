import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DashboardReplyTests(unittest.TestCase):
    def test_chart_insight_has_no_model_or_browser_timeout(self):
        reply_source = (ROOT / "modules" / "blueprint" / "dashboard" / "reply.py").read_text(encoding="utf-8")
        function = next(
            node for node in ast.parse(reply_source).body
            if isinstance(node, ast.FunctionDef) and node.name == "get_chart_insight_logic"
        )
        create_call = next(
            node for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "create"
        )
        self.assertNotIn("timeout", {keyword.arg for keyword in create_call.keywords})

        dashboard_source = (ROOT / "static" / "js" / "dashboard.js").read_text(encoding="utf-8")
        insight_start = dashboard_source.index("window.DashboardRenderer.fetchLlmInsight")
        insight_end = dashboard_source.index("window.DashboardRenderer.getSelectedYearTitle", insight_start)
        insight_source = dashboard_source[insight_start:insight_end]
        self.assertNotIn("AbortController", insight_source)
        self.assertNotIn("setTimeout", insight_source)

    def test_selected_stage_reports_finish_before_the_analysis_page_is_shown(self):
        control_source = (ROOT / "static" / "js" / "dashboard_control.js").read_text(encoding="utf-8")
        self.assertIn("stageReports.forEach(report => variantInsightTasks.push(", control_source)
        self.assertIn("() => window.DashboardRenderer.configureStageInsight(report)", control_source)
        self.assertIn("for (const task of variantInsightTasks) await completeInsight(task);", control_source)
        self.assertIn("if (!result?.success) result = await task();", control_source)
        self.assertIn("Promise.all(aiPromises.map", control_source)
        self.assertNotIn("Promise.allSettled(aiPromises.map", control_source)
        self.assertIn("chkTreatmentFirstCourse')?.checked && initialTreatmentSystem", control_source)
        self.assertIn("chkTreatmentSurgery')?.checked && initialSurgerySystem", control_source)

        stage_source = (ROOT / "static" / "js" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn("this.configureStageInsight(report, { generate: generateInsight });", stage_source)


if __name__ == "__main__":
    unittest.main()

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

    def test_field_definition_lookup_failure_does_not_skip_llm_generation(self):
        reply_source = (ROOT / "modules" / "blueprint" / "dashboard" / "reply.py").read_text(encoding="utf-8")
        function = next(
            node for node in ast.parse(reply_source).body
            if isinstance(node, ast.FunctionDef) and node.name == "get_chart_insight_logic"
        )
        get_conn_call = next(
            node for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "get_conn"
        )
        self.assertTrue(any(
            get_conn_call in list(ast.walk(try_node)) and try_node.handlers
            for try_node in ast.walk(function)
            if isinstance(try_node, ast.Try)
        ))

    def test_chart_insights_are_generated_sequentially_and_fail_independently(self):
        control_source = (ROOT / "static" / "js" / "dashboard_control.js").read_text(encoding="utf-8")
        self.assertIn("[...stageReports.slice(1), stageReports[0]].forEach(report => variantInsightTasks.push(", control_source)
        self.assertIn("() => window.DashboardRenderer.configureStageInsight(report)", control_source)
        self.assertIn("const insightTasks = [...variantInsightTasks];", control_source)
        self.assertIn("for (const task of insightTasks)", control_source)
        self.assertGreater(
            control_source.index("window.DashboardRenderer?.showAnnualDataContent();"),
            control_source.index("for (const task of insightTasks)"),
        )
        self.assertNotIn("Promise.all(aiPromises.map", control_source)
        self.assertIn("failedInsights += 1;", control_source)
        self.assertIn("chkTreatmentFirstCourse')?.checked && initialTreatmentSystem", control_source)
        self.assertIn("chkTreatmentSurgery')?.checked && initialSurgerySystem", control_source)
        self.assertIn("'#chartPane-TreatmentSurgery'].includes(targetSelector)", control_source)

        stage_source = (ROOT / "static" / "js" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn("this.configureStageInsight(report, { generate: generateInsight });", stage_source)
        self.assertIn("window.DashboardRenderer.fetchLlmInsightWithRetry = async function", stage_source)
        retry_start = stage_source.index("window.DashboardRenderer.fetchLlmInsightWithRetry")
        retry_end = stage_source.index("window.DashboardRenderer.getSelectedYearTitle", retry_start)
        retry_source = stage_source[retry_start:retry_end]
        self.assertIn("attempt < 3", retry_source)
        self.assertIn("if (result?.success) return result;", retry_source)

    def test_same_language_and_single_chart_controls_do_not_trigger_batch_regeneration(self):
        i18n_source = (ROOT / "static" / "js" / "dashboard_i18n.js").read_text(encoding="utf-8")
        self.assertIn("if (nextLanguage === (engine ? engine.language : language)) return;", i18n_source)

        template_source = (ROOT / "modules" / "blueprint" / "dashboard" / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertEqual(template_source.count('<button type="button" id="btnAi'), 8)


if __name__ == "__main__":
    unittest.main()

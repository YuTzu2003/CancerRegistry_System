import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LlmTaskPreviewTests(unittest.TestCase):
    def test_annual_report_writes_one_jsonl_request_per_chart(self):
        source = (ROOT / "modules" / "services" / "llm_tasks.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        create = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_llm_task")
        create_source = ast.unparse(create)
        self.assertIn("task_type == 'annual_report'", create_source)
        self.assertIn("'custom_id'", create_source)
        self.assertIn("'/v1/chat/completions'", create_source)
        self.assertIn("'payload': item", create_source)

    def test_preview_mode_never_posts_a_chart_insight_task(self):
        source = (ROOT / "static" / "js" / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        preview = (ROOT / "static" / "js" / "dashboard" / "dashboard_preview.js").read_text(encoding="utf-8")
        self.assertIn("window.dashboardPreviewMode = true", preview)
        self.assertLess(source.index("if (window.dashboardPreviewMode)"), source.index("fetch('/api/chart_insight'"))
    def test_preview_export_uses_selected_task_charts_and_completed_insights(self):
        preview = (ROOT / "static" / "js" / "dashboard" / "dashboard_preview.js").read_text(encoding="utf-8")
        dashboard = (ROOT / "static" / "js" / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        panel = (ROOT / "static" / "js" / "dashboard" / "llm_task_panel.js").read_text(encoding="utf-8")
        control = (ROOT / "modules" / "blueprint" / "dashboard" / "templates" / "control.html").read_text(encoding="utf-8")
        self.assertIn("button.dataset.target = paneSelector", preview)
        self.assertIn("dashboardPreviewNarratives", preview)
        self.assertIn("generateInsights: !isPreviewExport", dashboard)
        self.assertIn("?export=1", panel)
        self.assertNotIn('id="btnPrepareExport"', control)
    def test_preview_regeneration_requeues_the_same_annual_task(self):
        task_source = (ROOT / "modules" / "services" / "llm_tasks.py").read_text(encoding="utf-8")
        route_source = (ROOT / "modules" / "services" / "dashboard.py").read_text(encoding="utf-8")
        preview = (ROOT / "static" / "js" / "dashboard" / "dashboard_preview.js").read_text(encoding="utf-8")
        self.assertIn("def requeue_annual_report_item", task_source)
        self.assertIn("'retry.jsonl'", task_source)
        self.assertIn("/regenerate/<item_id>", route_source)
        self.assertIn("dashboard_refresh_after_preview", preview)
        self.assertIn("bindRegenerateButtons", preview)
    def test_worker_recovers_interrupted_running_tasks(self):
        source = (ROOT / "modules" / "services" / "llm_tasks.py").read_text(encoding="utf-8")
        self.assertIn("def recover_running_llm_tasks", source)
        worker = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "run_worker")
        self.assertIn("recover_running_llm_tasks()", ast.unparse(worker))

    def test_preview_route_checks_task_ownership_before_sending_image(self):
        source = (ROOT / "modules" / "services" / "dashboard.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        route = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "llm_task_preview")
        route_source = ast.unparse(route)
        self.assertIn("get_llm_task(task_id, session.get", route_source)
        self.assertIn("send_from_directory", route_source)


if __name__ == "__main__":
    unittest.main()
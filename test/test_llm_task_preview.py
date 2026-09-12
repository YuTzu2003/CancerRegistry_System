import ast
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from modules.services.llm_tasks import _batched_task_status
from modules.blueprint.dashboard.reply import _parse_bilingual_insights
from modules.blueprint.dashboard import chart_analytics


ROOT = Path(__file__).resolve().parents[1]


class LlmTaskPreviewTests(unittest.TestCase):
    def test_llm_insight_parser_repairs_an_invalid_backslash_escape(self):
        insights = _parse_bilingual_insights(r'{"zh-TW":"\ge 10","en":"\ge 10"}')
        self.assertEqual(insights, {'zh-TW': '>= 10', 'en': '>= 10'})

    def test_batched_task_requires_one_successful_output_per_input(self):
        inputs = [{'custom_id': 'stage'}, {'custom_id': 'gender-age'}]
        outputs = [{'custom_id': 'stage', 'result': {'success': True}}]
        self.assertEqual(_batched_task_status(inputs, outputs), 'partial_failed')

    def test_batched_task_rejects_duplicate_output_that_masks_a_missing_item(self):
        inputs = [{'custom_id': 'stage'}, {'custom_id': 'gender-age'}]
        outputs = [
            {'custom_id': 'stage', 'result': {'success': True}},
            {'custom_id': 'stage', 'result': {'success': True}},
        ]
        self.assertEqual(_batched_task_status(inputs, outputs), 'partial_failed')

    def test_batched_task_completes_only_when_all_items_succeed(self):
        inputs = [{'custom_id': 'stage'}, {'custom_id': 'gender-age'}]
        outputs = [
            {'custom_id': 'stage', 'result': {'success': True}},
            {'custom_id': 'gender-age', 'result': {'success': True}},
        ]
        self.assertEqual(_batched_task_status(inputs, outputs), 'completed')

    def test_histology_chart_keeps_dashboard_v3_layout_guards(self):
        dashboard = (ROOT / "static" / "js" / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        template = (ROOT / "modules" / "blueprint" / "dashboard" / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn("window.DashboardRenderer.histologyRowHeight", dashboard)
        self.assertIn("window.DashboardRenderer.histologyAxisLabel", dashboard)
        self.assertIn("window.DashboardRenderer.updateHistologyChart", dashboard)
        self.assertIn('colspan="3"', dashboard)
        self.assertIn('<th id="histologyNameHeader">組織型態</th>', template)
        self.assertNotIn('histologyCodeHeader', template)
        self.assertIn("replaceMerge: ['graphic']", dashboard)

    def test_histology_statistics_merge_codes_by_name_like_dashboard_v3(self):
        source = (ROOT / "modules" / "blueprint" / "dashboard" / "chart_analytics.py").read_text(encoding="utf-8")
        compare = (ROOT / "static" / "js" / "dashboard" / "dashboard_compare.js").read_text(encoding="utf-8")
        self.assertIn('key = (report_name_zh, report_name_en, is_in_situ)', source)
        self.assertNotIn('key = (icdo_code, report_name_zh, report_name_en)', source)
        self.assertIn('annual-histology-table compare-histology-table', compare)
        self.assertIn('colspan="3"', compare)

    def test_histology_statistics_merge_different_codes_with_the_same_name(self):
        cases = pd.DataFrame({
            'class': ['1', '2', '1'],
            'hist': ['8140', '8480', '8140'],
            'behavior': ['3', '3', '3'],
            'site': ['C18', 'C18', 'C18'],
            'year': ['2024', '2024', '2024'],
        })
        cols = {
            'class_col': 'class', 'hist_col': 'hist', 'behavior_col': 'behavior',
            'site_col': 'site', 'year_col': 'year', 'patient_id_col': None,
        }
        resolved = {'status': 'matched', 'icdo_code': 'unused', 'name_zh': '同一名稱', 'name_en': 'Same name'}
        with (
            patch.object(chart_analytics, 'get_histology_code_rules', return_value=[]),
            patch.object(chart_analytics, 'classify_cancer_group', return_value=None),
            patch.object(chart_analytics, 'is_blood_or_lymphoid', return_value=False),
            patch.object(chart_analytics, 'resolve_histology_code', return_value=resolved),
            patch.object(chart_analytics, 'should_append_in_situ', return_value=False),
        ):
            data = chart_analytics.calculate_histology_distribution(cases, cols)

        self.assertEqual(data, [{
            'name': '同一名稱', 'name_zh': '同一名稱', 'name_en': 'Same name',
            'count': 3, 'percentage': '100.0%',
        }])

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
        self.assertIn("queued: '處理中'", panel)
        self.assertNotIn('id="btnPrepareExport"', control)

    def test_preview_renders_dashboard_v3_stage_treatment_tables(self):
        preview = (ROOT / "static" / "js" / "dashboard" / "dashboard_preview.js").read_text(encoding="utf-8")
        self.assertIn("renderStageFirstCourseTables?.(chartData.stageFirstCourseData || [], year, cancer)", preview)
        self.assertIn("renderStageSurgeryTables?.(chartData.stageSurgeryData || [], year, cancer)", preview)
    def test_preview_regeneration_requeues_the_same_annual_task(self):
        task_source = (ROOT / "modules" / "services" / "llm_tasks.py").read_text(encoding="utf-8")
        route_source = (ROOT / "modules" / "services" / "dashboard.py").read_text(encoding="utf-8")
        preview = (ROOT / "static" / "js" / "dashboard" / "dashboard_preview.js").read_text(encoding="utf-8")
        self.assertIn("def requeue_annual_report_item", task_source)
        self.assertIn("'retry.jsonl'", task_source)
        self.assertIn("/regenerate/<item_id>", route_source)
        self.assertIn("dashboard_refresh_after_preview", preview)
        self.assertIn("bindRegenerateButtons", preview)
    def test_comparison_report_uses_one_batched_job_and_preview(self):
        task_source = (ROOT / "modules" / "services" / "llm_tasks.py").read_text(encoding="utf-8")
        route_source = (ROOT / "modules" / "services" / "dashboard.py").read_text(encoding="utf-8")
        compare_source = (ROOT / "static" / "js" / "dashboard" / "dashboard_compare.js").read_text(encoding="utf-8")
        template = (ROOT / "modules" / "blueprint" / "dashboard" / "templates" / "compare.html").read_text(encoding="utf-8")
        migration = (ROOT / "deploy" / "database" / "llm_task_worker.sql").read_text(encoding="utf-8")
        self.assertIn("'comparison_report'", task_source)
        self.assertIn("get_compare_insight_logic", task_source)
        self.assertIn("comparison_report_job_route", route_source)
        self.assertIn("comparison_preview", route_source)
        self.assertIn("/api/dashboard/comparison-report-job", compare_source)
        self.assertIn("comparisonPreviewData", compare_source)
        self.assertIn("regeneratePreviewNarrative", compare_source)
        self.assertIn("/regenerate/${encodeURIComponent(itemId)}", compare_source)
        self.assertIn('data-llm-task-type="comparison_report"', template)
        self.assertIn("N'comparison_report'", migration)
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

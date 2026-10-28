import unittest

from modules.blueprint.dashboard.llm_tasks import _batched_task_status, _bilingual_progress


class AnnualExportReadinessTests(unittest.TestCase):
    def setUp(self):
        self.inputs = [{'custom_id': 'first'}, {'custom_id': 'second'}]
        self.complete = {'success': True, 'insights': {'zh-TW': '中文敘述', 'en': 'English narrative'}}
        self.chinese_only = {'success': True, 'insights': {'zh-TW': '中文敘述', 'en': '  '}}

    def test_progress_counts_only_complete_bilingual_pairs(self):
        outputs = [
            {'custom_id': 'first', 'result': self.complete},
            {'custom_id': 'second', 'result': self.chinese_only},
        ]
        self.assertEqual(_bilingual_progress(self.inputs, outputs), 1)
        self.assertEqual(_batched_task_status(self.inputs, outputs, require_bilingual=True), 'partial_failed')

    def test_complete_status_requires_every_pair(self):
        outputs = [{'custom_id': item['custom_id'], 'result': self.complete} for item in self.inputs]
        self.assertEqual(_bilingual_progress(self.inputs, outputs), 2)
        self.assertEqual(_batched_task_status(self.inputs, outputs, require_bilingual=True), 'completed')

    def test_duplicate_or_unexpected_results_do_not_advance_progress(self):
        outputs = [
            {'custom_id': 'first', 'result': self.complete},
            {'custom_id': 'first', 'result': self.complete},
            {'custom_id': 'other', 'result': self.complete},
        ]
        self.assertEqual(_bilingual_progress(self.inputs, outputs), 1)
        self.assertEqual(_batched_task_status(self.inputs, outputs, require_bilingual=True), 'failed')


if __name__ == '__main__':
    unittest.main()

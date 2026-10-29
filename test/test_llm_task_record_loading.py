import json
from pathlib import Path
import unittest
from unittest.mock import patch

from modules.blueprint.dashboard import llm_tasks


class LlmTaskRecordLoadingTests(unittest.TestCase):
    def test_one_damaged_output_does_not_hide_other_results_or_change_file(self):
        valid = {'custom_id': 'chart-1', 'result': {'success': True}}
        original = json.dumps(valid).encode('utf-8') + b'\n\x88broken\n'
        with patch.object(Path, 'exists', return_value=True), patch.object(Path, 'read_bytes', return_value=original), patch.object(Path, 'write_bytes') as write:
            with self.assertLogs(level='WARNING'):
                rows = llm_tasks._rows('annual_report', 'task-id', 'output.jsonl')
        self.assertEqual(rows, [valid])
        write.assert_not_called()


if __name__ == '__main__':
    unittest.main()

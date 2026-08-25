from io import BytesIO
from types import SimpleNamespace
import unittest

from openpyxl import Workbook

from app import app
from modules.blueprint.dashboard import histology_code


class HistologyCodeImportTest(unittest.TestCase):
    columns = [
        "HistCode_ID",
        "CodeYear",
        "CancerGroupKey",
        "CancerGroup_zh",
        "CancerGroup_en",
        "hist",
        "behavior",
        "hist_zh",
        "hist_en",
    ]

    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["id"] = "test"
        self.original_get_conn = histology_code.get_conn
        self.original_get_mapping_data = histology_code._get_mapping_data
        self.imported_rows = []
        cursor = SimpleNamespace(executemany=self._executemany)
        self.connection = SimpleNamespace(
            cursor=lambda: cursor,
            commit=lambda: None,
            rollback=lambda: None,
            close=lambda: None,
        )
        histology_code.get_conn = lambda: self.connection
        histology_code._get_mapping_data = lambda *args: (self.columns, [])

    def tearDown(self):
        histology_code.get_conn = self.original_get_conn
        histology_code._get_mapping_data = self.original_get_mapping_data

    def _executemany(self, _, rows):
        self.imported_rows.extend(rows)

    def _workbook(self, rows):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(histology_code._IMPORT_COLUMNS)
        for row in rows:
            worksheet.append(row)
        stream = BytesIO()
        workbook.save(stream)
        stream.seek(0)
        return stream

    def test_import_adds_rows_matching_the_template(self):
        response = self.client.post(
            "/dashboard/histology-code-mapping/import",
            data={
                "import_file": (
                    self._workbook([[112, "Lung", "肺癌", "Lung cancer", 8140, 3, "腺癌", "Adenocarcinoma"]]),
                    "mapping.xlsx",
                )
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.imported_rows[0][0], "112")
        self.assertEqual(len(self.imported_rows), 1)

    def test_import_rejects_an_incomplete_row(self):
        response = self.client.post(
            "/dashboard/histology-code-mapping/import",
            data={
                "import_file": (
                    self._workbook([[112, "Lung", "肺癌", "Lung cancer", 8140, None, "腺癌", "Adenocarcinoma"]]),
                    "mapping.xlsx",
                )
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.imported_rows, [])


if __name__ == "__main__":
    unittest.main()

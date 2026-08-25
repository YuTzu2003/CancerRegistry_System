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
        self.original_get_mapping_columns = histology_code._get_mapping_columns
        self.imported_rows = []
        self.executed_queries = []
        cursor = SimpleNamespace(execute=self._execute, executemany=self._executemany)
        self.connection = SimpleNamespace(
            cursor=lambda: cursor,
            commit=lambda: None,
            rollback=lambda: None,
            close=lambda: None,
        )
        histology_code.get_conn = lambda: self.connection
        histology_code._get_mapping_data = lambda *args: (self.columns, [])
        histology_code._get_mapping_columns = lambda: self.columns

    def tearDown(self):
        histology_code.get_conn = self.original_get_conn
        histology_code._get_mapping_data = self.original_get_mapping_data
        histology_code._get_mapping_columns = self.original_get_mapping_columns

    def _executemany(self, _, rows):
        self.imported_rows.extend(rows)

    def _execute(self, query, *values):
        self.executed_queries.append((query, values))

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

    def test_batch_delete_requires_a_selected_row(self):
        response = self.client.post("/dashboard/histology-code-mapping/delete-selected")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.executed_queries, [])

    def test_create_update_and_delete_routes_execute_the_expected_queries(self):
        values = {
            column: value
            for column, value in zip(
                self.columns[1:],
                [112, "Lung", "肺癌", "Lung cancer", 8140, 3, "腺癌", "Adenocarcinoma"],
            )
        }
        values.update({"return_year": "112", "return_column": "hist", "return_q": "8140"})

        create_response = self.client.post("/dashboard/histology-code-mapping/create", data=values)
        update_response = self.client.post("/dashboard/histology-code-mapping/7/update", data=values)
        delete_response = self.client.post(
            "/dashboard/histology-code-mapping/7/delete",
            data={"return_year": "112", "return_column": "hist", "return_q": "8140"},
        )
        batch_delete_response = self.client.post(
            "/dashboard/histology-code-mapping/delete-selected",
            data={
                "histcode_ids": ["7", "8"],
                "return_year": "112",
                "return_column": "hist",
                "return_q": "8140",
            },
        )

        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(delete_response.status_code, 302)
        self.assertEqual(batch_delete_response.status_code, 302)
        self.assertEqual(len(self.imported_rows), 1)
        self.assertTrue(self.executed_queries[0][0].startswith("UPDATE"))
        self.assertTrue(self.executed_queries[1][0].startswith("DELETE"))
        self.assertTrue(self.executed_queries[2][0].startswith("DELETE"))
        self.assertEqual(self.executed_queries[2][1], ("7", "8"))
        self.assertIn("year=112", create_response.headers["Location"])


if __name__ == "__main__":
    unittest.main()

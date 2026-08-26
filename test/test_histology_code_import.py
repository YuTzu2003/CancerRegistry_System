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
            session["userid"] = "tester"
            session["histology_mapping_access_token"] = "test-access-token"
            session["histology_mapping_access_user"] = "tester"
        self.original_get_conn = histology_code.get_conn
        self.original_get_mapping_data = histology_code._get_mapping_data
        self.original_get_mapping_columns = histology_code._get_mapping_columns
        self.imported_rows = []
        self.executed_queries = []
        self.key_is_valid = False
        cursor = SimpleNamespace(
            execute=self._execute,
            executemany=self._executemany,
            fetchone=self._fetchone,
        )
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

    def _fetchone(self):
        return (1,) if self.key_is_valid else None

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
            "/dashboard/histology-code/import",
            data={
                "access_token": "test-access-token",
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
            "/dashboard/histology-code/import",
            data={
                "access_token": "test-access-token",
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
        response = self.client.post(
            "/dashboard/histology-code/delete-selected",
            data={"access_token": "test-access-token"},
        )

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
        values.update(
            {
                "access_token": "test-access-token",
                "return_year": "112",
                "return_column": "hist",
                "return_q": "8140",
            }
        )

        create_response = self.client.post("/dashboard/histology-code/create", data=values)
        update_response = self.client.post("/dashboard/histology-code/7/update", data=values)
        delete_response = self.client.post(
            "/dashboard/histology-code/7/delete",
            data={
                "access_token": "test-access-token",
                "return_year": "112",
                "return_column": "hist",
                "return_q": "8140",
            },
        )
        batch_delete_response = self.client.post(
            "/dashboard/histology-code/delete-selected",
            data={
                "access_token": "test-access-token",
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

    def test_write_routes_reject_requests_without_page_key_access(self):
        with self.client.session_transaction() as session:
            session.pop("histology_mapping_access_token")

        response = self.client.post("/dashboard/histology-code/create")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.imported_rows, [])
        self.assertEqual(self.executed_queries, [])

    def test_key_verification_grants_access_only_to_the_logged_in_account(self):
        self.key_is_valid = True

        response = self.client.post(
            "/dashboard/histology-code/access",
            data={"api_key": "approved-key", "return_year": "112"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("UserID = ? AND API_key = ?", self.executed_queries[0][0])
        self.assertEqual(self.executed_queries[0][1], ("tester", "approved-key"))
        with self.client.session_transaction() as session:
            self.assertEqual(session["histology_mapping_access_user"], "tester")
            self.assertTrue(session["histology_mapping_access_token"])

    def test_mapping_page_requires_key_again_when_opened_without_access_token(self):
        response = self.client.get("/dashboard/histology-code")

        self.assertEqual(response.status_code, 200)
        self.assertIn("組織型態資料授權", response.get_data(as_text=True))

    def test_admin_can_modify_without_a_key(self):
        with self.client.session_transaction() as session:
            session["position"] = "Admin"
            session.pop("histology_mapping_access_token")

        response = self.client.post(
            "/dashboard/histology-code/create",
            data=dict(
                zip(
                    self.columns[1:],
                    [112, "Lung", "肺癌", "Lung cancer", 8140, 3, "腺癌", "Adenocarcinoma"],
                )
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.imported_rows), 1)

    def test_create_rejects_empty_or_non_numeric_values(self):
        empty_response = self.client.post(
            "/dashboard/histology-code/create",
            data={"access_token": "test-access-token"},
        )
        invalid_response = self.client.post(
            "/dashboard/histology-code/create",
            data={
                "access_token": "test-access-token",
                **dict(
                    zip(
                        self.columns[1:],
                        ["one", "Lung", "肺癌", "Lung cancer", "eight", 3, "腺癌", "Adenocarcinoma"],
                    )
                ),
            },
        )

        self.assertEqual(empty_response.status_code, 302)
        self.assertEqual(invalid_response.status_code, 302)
        self.assertEqual(self.imported_rows, [])


if __name__ == "__main__":
    unittest.main()

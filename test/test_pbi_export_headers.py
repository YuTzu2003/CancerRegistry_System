import unittest

from modules.blueprint.dashboard.pbi_export import _pbix_column_name


class PowerBiHeaderTests(unittest.TestCase):
    def test_registry_identifiers_are_removed(self):
        self.assertEqual(_pbix_column_name("1.2病歷號碼"), "病歷號碼")
        self.assertEqual(
            _pbix_column_name("3.3.申報醫院診斷性及分期性手術處置"),
            "申報醫院診斷性及分期性手術處置",
        )

    def test_template_header_exceptions(self):
        self.assertEqual(_pbix_column_name("3.4臨床 T"), "臨床T")
        self.assertEqual(
            _pbix_column_name("4.2.1.8未放射治療原因/放射治療執行狀態"),
            "放射治療執行狀態",
        )
        self.assertEqual(_pbix_column_name("3.19其他分期系統期別(臨床分期)"),
                         "其他分期系統期別(臨床分期)\n")


if __name__ == "__main__":
    unittest.main()

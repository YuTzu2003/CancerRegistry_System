import unittest
from decimal import Decimal

from modules.blueprint.survival_report.models import (
    AnnualObservation,
    ParsedWorkbook,
    SourceFormat,
    StageSeries,
    SurvivalEstimate,
)
from modules.blueprint.survival_report.report_builder import build_report_batch


def available(rate: str) -> SurvivalEstimate:
    value = Decimal(rate)
    return SurvivalEstimate(
        rate=value,
        ci_low=value - 1,
        ci_high=value + 1,
        value_status="available",
    )


def stage_series(
    stage: str,
    rate: str,
    *,
    cancer: str = "膀胱癌",
    staging_system: str = "AJCC",
) -> StageSeries:
    estimate = available(rate)
    return StageSeries(
        cancer=cancer,
        staging_system=staging_system,
        stage=stage,
        observations=(
            AnnualObservation(
                follow_up_year=1,
                analyzable_count=10,
                censored_count=2,
                death_count=3,
                observed=estimate,
                source_row=10,
            ),
        ),
        adjusted=estimate,
        nationwide=available("53.53"),
        medical_center=available("53.63"),
        non_medical_center=available("53.13"),
    )


class SurvivalReportWarningTests(unittest.TestCase):
    def test_default_table_order_matches_the_reference_deck(self):
        reference_specs = [
            ("大腸癌-all", "AJCC"),
            ("大腸癌-結腸癌", "AJCC"),
            ("大腸癌-直腸癌", "AJCC"),
            ("子宮頸癌", "FIGO"),
            ("子宮體癌", "FIGO"),
            ("卵巢癌", "FIGO"),
            ("女性乳癌", "AJCC"),
            ("肺癌 非小細胞癌-all", "AJCC"),
            ("肺癌 非小細胞癌-腺癌", "AJCC"),
            ("肺癌 非小細胞癌-鱗狀細胞癌", "AJCC"),
            ("肺癌 小細胞癌", "AJCC"),
            ("食道癌", "AJCC"),
            ("肝癌", "BCLC"),
            ("胃癌", "AJCC"),
            ("鼻咽癌", "AJCC"),
            ("口腔癌", "AJCC"),
            ("下咽癌", "AJCC"),
            ("喉癌", "AJCC"),
            ("口咽癌_p16+", "AJCC"),
            ("口咽癌_p16-", "AJCC"),
            ("膀胱癌", "AJCC"),
            ("攝護腺癌", "AJCC"),
        ]
        workbook = ParsedWorkbook(
            source_filename="local.xlsx",
            source_format=SourceFormat.OOXML,
            hospital_name="本院",
            period_start=2019,
            period_end=2023,
            target_years=1,
            stage_series=tuple(
                stage_series(
                    "第1期",
                    str(60 + index),
                    cancer=cancer,
                    staging_system=staging_system,
                )
                for index, (cancer, staging_system) in enumerate(
                    [("甲狀腺癌", "AJCC"), *reversed(reference_specs)]
                )
            ),
        )

        ordered_titles = [
            table.display_title
            for table in build_report_batch([workbook]).decks[0].ordered_tables
        ]

        self.assertEqual(
            ordered_titles,
            [
                "大腸癌-all存活率",
                "大腸癌-結腸癌存活率",
                "大腸癌-直腸癌存活率",
                "子宮頸癌FIGO分期存活率",
                "子宮體癌FIGO分期存活率",
                "卵巢癌FIGO分期存活率",
                "女性乳癌存活率",
                "肺癌 非小細胞癌-all存活率",
                "肺癌 非小細胞癌-腺癌存活率",
                "肺癌 非小細胞癌-鱗狀細胞癌存活率",
                "肺癌 小細胞癌存活率",
                "食道癌存活率",
                "肝癌BCLC分期存活率",
                "胃癌存活率",
                "鼻咽癌存活率",
                "口腔癌存活率",
                "下咽癌存活率",
                "喉癌存活率",
                "口咽癌_p16+存活率",
                "口咽癌_p16-存活率",
                "膀胱癌存活率",
                "攝護腺癌存活率",
                "甲狀腺癌存活率",
            ],
        )

    def test_unstaged_aliases_from_different_hospitals_merge_into_one_row(self):
        local = ParsedWorkbook(
            source_filename="local.xlsx",
            source_format=SourceFormat.OOXML,
            hospital_name="本院",
            period_start=2019,
            period_end=2023,
            target_years=1,
            stage_series=(stage_series("不分期別 (含不詳)", "44.10"),),
        )
        other = ParsedWorkbook(
            source_filename="other.xlsx",
            source_format=SourceFormat.OOXML,
            hospital_name="A醫院",
            period_start=2019,
            period_end=2023,
            target_years=1,
            stage_series=(stage_series("不分期別", "58.06"),),
        )

        table = build_report_batch([local, other]).tables[0]

        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].stage, "不分期別 (含不詳)")
        self.assertEqual(
            [value.estimate.rate for value in table.rows[0].hospital_values],
            [Decimal("44.10"), Decimal("58.06")],
        )

    def test_missing_death_count_stays_empty_without_creating_warning(self):
        estimate = available("68.01")
        series = StageSeries(
            cancer="直腸癌",
            staging_system="AJCC",
            stage="第1期",
            observations=(
                AnnualObservation(
                    follow_up_year=1,
                    analyzable_count=37,
                    censored_count=None,
                    death_count=None,
                    observed=estimate,
                    source_row=10,
                ),
            ),
            adjusted=estimate,
            nationwide=available("79.46"),
            medical_center=available("80.52"),
            non_medical_center=available("78.21"),
        )
        workbook = ParsedWorkbook(
            source_filename="missing-death.xlsx",
            source_format=SourceFormat.OOXML,
            hospital_name="本院",
            period_start=2019,
            period_end=2023,
            target_years=1,
            stage_series=(series,),
        )

        batch = build_report_batch([workbook])

        table = batch.tables[0]
        self.assertIsNone(table.rows[0].death_count)
        self.assertNotIn(
            "missing_death_count",
            [issue.code for issue in table.issues],
        )
        self.assertEqual(batch.decks[0].warning_count, 0)


if __name__ == "__main__":
    unittest.main()

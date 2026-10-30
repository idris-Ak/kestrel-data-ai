"""Reviewed source profiles. Source text is data, never executable configuration."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Segment:
    sheet: str
    header_row: int
    first_row: int
    last_row: int | None
    headers: tuple[str, ...]
    date_column: str
    department_column: str
    rating_column: str
    comment_column: str
    date_format: str
    scale_max: int
    direction: str = "unspecified"
    period_start: str = "2025-10-01"
    period_end: str = "2026-10-01"
    reference_column: str | None = None


@dataclass(frozen=True)
class Source:
    path: str
    kind: str
    dealer: str | None = None
    segments: tuple[Segment, ...] = ()
    expected_sheets: tuple[str, ...] = ()
    context_rows: tuple[tuple[str, int, str], ...] = ()
    required_notes: tuple[tuple[str, str], ...] = ()
    encoding: str = "utf-8-sig"
    delimiter: str = ","

    def profile(self) -> dict:
        return {"registry_version": 1, "expected_data_records": EXPECTED_RECORDS[self.path], **asdict(self)}


GEELONG_HEADER = ("Date", "Department", "Rating", "Feedback", "Customer")
CHERMSIDE_HEADER = ("Date", "Department", "Model", "Rating", "Comments", "Ref", "Customer No")
DEALER_HEADER = ("dealer_code", "dealership_name", "suburb", "state", "region", "brands", "status", "closed_date")
BUSINESS_HEADER = ("dealer_code", "month", "vehicles_sold", "sales_revenue_aud", "service_jobs", "service_revenue_aud", "parts_transactions", "parts_revenue_aud")
AGGREGATE_HEADER = ("Month", "Department", "1", "2", "3", "4", "5", "Grand Total")

SOURCES = (
    Source("reference/dealerships.csv", "dealerships"),
    Source("reference/monthly_revenue.csv", "business"),
    Source("feedback/boxhill_survey_export_2025Q4.csv", "feedback", "VIC05", (
        Segment("CSV", 1, 2, None,
                ("response_id", "submitted_at", "department", "csat", "verbatim", "vehicle", "dms_customer_no"),
                "submitted_at", "department", "csat", "verbatim", "%Y-%m-%d %H:%M:%S", 5,
                period_end="2026-01-01", reference_column="response_id"),
    )),
    Source("feedback/Geelong Feedback.xlsx", "feedback", "VIC06", (
        Segment("2025", 4, 5, None, GEELONG_HEADER, "Date", "Department", "Rating", "Feedback", "%d/%m/%y", 5,
                "low_is_good", period_end="2026-01-01"),
        Segment("2026", 4, 5, None, GEELONG_HEADER, "Date", "Department", "Rating", "Feedback", "%d/%m/%y", 5,
                "high_is_good", period_start="2026-01-01"),
    ), ("2025", "2026"), tuple((s, r, role) for s in ("2025", "2026") for r, role in ((1, "title"), (2, "rating_legend"), (3, "blank")))),
    Source("feedback/Chermside Q1 2026 FINAL.xlsx", "feedback", "QLD01", (
        Segment("Feedback", 1, 2, None, CHERMSIDE_HEADER, "Date", "Department", "Rating", "Comments", "excel_datetime", 5,
                period_start="2026-01-01", period_end="2026-04-01", reference_column="Ref"),
    ), ("Feedback",)),
    Source("feedback/Chermside Q1 2026 FINAL v2.xlsx", "feedback", "QLD01", (
        Segment("Feedback", 1, 2, None, CHERMSIDE_HEADER, "Date", "Department", "Rating", "Comments", "excel_datetime", 5,
                period_start="2026-01-01", period_end="2026-04-01", reference_column="Ref"),
    ), ("Feedback",)),
    Source("feedback/Ringwood feedback Q1 2026.xlsx", "feedback", "VIC02", (
        Segment("Feedback", 1, 2, 35, ("Date Received", "Department", "Score (1-5)", "Customer comments", "Followed up?"),
                "Date Received", "Department", "Score (1-5)", "Customer comments", "%d/%m/%Y", 5,
                period_start="2026-01-01", period_end="2026-02-01"),
        Segment("Feedback", 37, 38, None, ("Date", "Department", "Model", "Score (out of 10)", "Customer comments", "Follow up (Y/N)", "Staff"),
                "Date", "Department", "Score (out of 10)", "Customer comments", "%d/%m/%Y", 10,
                period_start="2026-02-01", period_end="2026-04-01"),
    ), ("Feedback",), (("Feedback", 36, "layout_change"),)),
    Source("feedback/liverpool_q3_2026.csv", "feedback", "NSW04", (
        Segment("CSV", 1, 2, None, ("Date", "Department", "Customer", "Phone", "Rego", "Rating", "Feedback"),
                "Date", "Department", "Rating", "Feedback", "%m/%d/%Y", 5,
                period_start="2026-07-01", period_end="2026-10-01"),
    )),
    Source("feedback/Noosa feedback cards.xlsx", "feedback", "QLD05", (
        Segment("Cards", 1, 2, None, ("Date", "Department", "Rating", "Comments", "Card given by"),
                "Date", "Department", "Rating", "Comments", "excel_datetime", 5),
    ), ("Cards",), required_notes=(("Cards", "C1"),)),
    Source("feedback/Toowoomba Q4 2025 summary.xlsx", "aggregate", "QLD06", expected_sheets=("Summary",),
           context_rows=(("Summary", 1, "title"), ("Summary", 2, "blank"), ("Summary", 10, "control_total"))),
)

OLDER_CHERMSIDE = "feedback/Chermside Q1 2026 FINAL.xlsx"
NEWER_CHERMSIDE = "feedback/Chermside Q1 2026 FINAL v2.xlsx"

# Independent source-row controls from the discovery audit, not deletion targets.
EXPECTED_RECORDS = {
    "reference/dealerships.csv": 24,
    "reference/monthly_revenue.csv": 288,
    "feedback/boxhill_survey_export_2025Q4.csv": 64,
    "feedback/Geelong Feedback.xlsx": 304,
    OLDER_CHERMSIDE: 112,
    NEWER_CHERMSIDE: 118,
    "feedback/Ringwood feedback Q1 2026.xlsx": 112,
    "feedback/liverpool_q3_2026.csv": 85,
    "feedback/Noosa feedback cards.xlsx": 49,
    "feedback/Toowoomba Q4 2025 summary.xlsx": 6,
}

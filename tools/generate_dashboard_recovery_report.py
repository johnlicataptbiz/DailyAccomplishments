"""
Generate a dashboard recovery PDF report for the Daily Accomplishments Tracker.

The report summarizes the recovery process for the dashboard, including
restoration checkpoints, validation steps, and next actions. The script is
standalone and can be re-run whenever a new recovery cycle is completed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF


REPORT_TITLE = "DailyAccomplishments Dashboard Recovery Report"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / f"{REPORT_TITLE}.pdf"


def _format_timestamp() -> str:
    """Return a human-friendly timestamp for the report header."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


class RecoveryReportPDF(FPDF):
    """Lightweight PDF builder for the recovery report."""

    def header(self) -> None:  # pragma: no cover - layout code
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, REPORT_TITLE, ln=1)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 8, f"Generated: {_format_timestamp()}", ln=1)
        self.ln(4)

    def footer(self) -> None:  # pragma: no cover - layout code
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _add_section(pdf: RecoveryReportPDF, title: str, bullets: list[str]) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, title, ln=1)
    pdf.set_font("Helvetica", "", 11)
    for bullet in bullets:
        pdf.multi_cell(0, 6, f"- {bullet}")
        pdf.set_x(pdf.l_margin)  # Reset X position for fpdf2 compatibility
    pdf.ln(2)


def build_report(output_path: Path) -> Path:
    """Build and persist the recovery report to the given path."""
    sections: dict[str, list[str]] = {
        "Objective": [
            "Document the current dashboard recovery status and actions taken.",
            "Provide a repeatable checklist for restoring dashboards after data loss or corruption.",
            "Capture follow-up improvements to harden the pipeline.",
        ],
        "Recovery Timeline": [
            "Validated backups under logs/daily and verified integrity of JSONL payloads.",
            "Rebuilt aggregated metrics using tools/auto_report.py to refresh charts and summaries.",
            "Regenerated dashboard.html and static assets to ensure Chart.js views load cleanly.",
        ],
        "Verification": [
            "Ran smoke tests (tests/test_smoke.py) to confirm core timeline calculations are stable.",
            "Reviewed focus_summary.csv for anomalous values or missing intervals.",
            "Opened dashboard.html locally to confirm category distribution, interruptions, and sessions render correctly.",
        ],
        "Remediation Actions": [
            "Restored corrupted daily entries from the latest non-empty backup in logs.backup-*/daily.",
            "Rebuilt focus and category artifacts (CSV/SVG) with generate_charts.sh for visual parity.",
            "Rotated API credentials in credentials/ and rehydrated config.json from config.json.example defaults where needed.",
        ],
        "Hardening Recommendations": [
            "Enable automated integrity checks via tests/test_intervals.py on CI to catch overlap regressions early.",
            "Schedule nightly snapshots of reports/ and dashboard assets to offsite storage.",
            "Document manual recovery owners and expected response times in FUTURE_UPDATES.md for quick escalation.",
        ],
        "Next Steps": [
            "Run python tools/auto_report.py after the next sync window to confirm metrics match recovered data.",
            "Share the regenerated PDF with stakeholders and store it alongside the release artifacts.",
            "Track any new edge cases discovered during recovery in docs/design/IMPROVEMENTS.md for future sprints.",
        ],
    }

    pdf = RecoveryReportPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    for title, bullets in sections.items():
        _add_section(pdf, title, bullets)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the dashboard recovery PDF report.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Destination for the PDF report (default: {DEFAULT_OUTPUT.name}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = build_report(args.output)
    print(f"Recovery report written to: {output_path}")


if __name__ == "__main__":
    main()

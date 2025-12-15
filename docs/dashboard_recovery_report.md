# Dashboard Recovery Report

This recovery report documents the steps used to restore the Daily Accomplishments dashboard and provides a repeatable process for future incidents. The companion script `tools/generate_dashboard_recovery_report.py` renders a PDF version named **DailyAccomplishments Dashboard Recovery Report.pdf**.

## Contents
- Objective and scope of the recovery
- Recovery timeline checkpoints
- Verification steps to validate dashboards and data
- Remediation actions applied during restoration
- Hardening recommendations for future incidents
- Next steps and follow-up tasks

## Regenerating the PDF
1. Ensure dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
2. Generate the report (default output is created in the repository root):
   ```bash
   python tools/generate_dashboard_recovery_report.py
   ```
3. Optionally, write to a custom location:
   ```bash
   python tools/generate_dashboard_recovery_report.py --output /tmp/recovery.pdf
   ```

The generated PDF is meant to be shared with stakeholders and stored alongside release artifacts for traceability.

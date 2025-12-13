# Hosting `reports/` via GitHub Pages

This project publishes generated per-date reports under the `reports/` directory and uses a dedicated branch `reports-gh-pages` for static hosting.

Steps to enable GitHub Pages to serve `reports/` from the `reports-gh-pages` branch:

1. Open the repository on GitHub and go to `Settings` → `Pages`.
2. Under "Source", choose the branch `reports-gh-pages` and the root (`/`) folder.
3. Save and wait a minute for GitHub Pages to build and publish.

Verification commands (local / CI):

 - Check the HTTP status of a known report (replace domain):
   ```bash
   curl -I https://<your-domain-or-username>.github.io/<repo>/reports/2025-12-05/ActivityReport-2025-12-05.json || true
   ```

 - Fetch content to confirm it's the canonical report:
   ```bash
   curl -s https://<your-domain-or-username>.github.io/<repo>/reports/2025-12-05/ActivityReport-2025-12-05.json | head -n 40
   ```

Notes:
- If you prefer a custom domain or different Pages branch, adjust the branch selection accordingly.
- The repository includes a workflow that publishes `./reports` to the `reports-gh-pages` branch automatically (`.github/workflows/generate_and_publish_reports.yml`). After enabling Pages, the published reports should be served at the Pages URL.

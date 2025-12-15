# Railway auto-deploy setup

This project can auto-deploy to Railway whenever the `main` branch is updated.

Steps to connect and ensure 30-minute updates:

1. Connect repository to Railway
   - Open https://railway.app and go to your project (or create one).
   - In the project, go to Settings -> GitHub (or Deployments) and connect the `johnlicataptbiz/DailyAccomplishments` repository.
   - Select the branch to auto-deploy (typically `main`). Enable automatic deploys.

2. Confirm Railway build/start
   - Railway will use the repository files. Confirm the build command and start command match this repo (it has a `Dockerfile` and `railway.json`).
   - If Railway builds the Docker image, ensure any generated artifacts are present at build time (the scheduled workflow commits generated files to `main` before Railway builds).

3. Add GitHub secrets (optional but recommended)
   - If your repository has branch protection that prevents pushes from `GITHUB_TOKEN`, create a Personal Access Token (PAT) with `repo` scope and add it as a repository secret named `PAT`.
   - If you want to trigger Railway via its CLI or API from workflows, add a secret `RAILWAY_TOKEN` (from Railway account settings).

4. Verify scheduled updates
   - The repository contains a GitHub Actions workflow `.github/workflows/scheduled-update.yml` that runs every 30 minutes. It runs `generate_reports.sh` or `tools/generate_reports.py`, commits any changes, and pushes to `main`.
   - To test manually: in GitHub Actions, run the workflow via "Run workflow" (workflow_dispatch) and observe whether it commits files and triggers Railway.

5. Troubleshooting
   - If the workflow fails to push due to branch protection: add `PAT` as described above.
   - If Railway does not redeploy: check the project's Deployments tab and the build logs for errors.


Minimal checklist
- [ ] Repository connected to Railway and auto-deploy enabled for `main`
- [ ] `.github/workflows/scheduled-update.yml` present (committed)
- [ ] `generate_reports.sh` or `tools/generate_reports.py` runs non-interactively
- [ ] `PAT` secret added if branch protection blocks GITHUB_TOKEN
- [ ] Manual workflow run confirmed a commit and Railway deployment

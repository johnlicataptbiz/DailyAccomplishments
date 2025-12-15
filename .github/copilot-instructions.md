# GitHub Copilot Instructions for DailyAccomplishments

## Project Overview

DailyAccomplishments is a productivity tracking and reporting application that aggregates activity data from multiple platforms and generates daily reports with visualizations.

### Purpose
- Track daily accomplishments across multiple platforms
- Categorize activities (Coding, Research, Communication, Meetings, Other)
- Generate reports and visualizations
- Provide a web dashboard for viewing results

### Key Integrations
- **HubSpot**: CRM activity tracking
- **Aloware**: Communication platform
- **Monday.com**: Project management boards
- **Slack**: Team communication messages
- **Google Calendar**: Meeting and event tracking

## Project Structure

### Configuration Files
- **config.json**: Main configuration file containing:
  - Tracking settings (hours, timezone, categories)
  - Integration credentials and settings
  - Report generation preferences
  - Notification settings (email, Slack webhooks)
  - Data retention policies

### File Handling
- **CSV files**: Data files that may contain trailing whitespace (configured in .gitattributes)
- **Visualizations**: Prefer SVG charts; avoid committing new binary image artifacts in PRs
- **Credentials**: Stored in `credentials/` directory (excluded from git)
- **Logs**: Stored in `logs/daily` and `logs/archive` directories

## Build and Deployment

### Docker
The application uses Docker for deployment:
```bash
docker build -t daily-accomplishments .
docker run -p 8000:8000 daily-accomplishments
```

### Dependencies
- **Python 3.12**: Runtime environment
- **matplotlib**: For generating charts and visualizations
- System dependencies (installed in Docker): matplotlib runtime deps (freetype, etc.)

### Web Server
- Default port: 8000
- Serves reports and dashboard via Python's built-in HTTP server
- Static files served from `gh-pages/` directory

## Coding Standards and Conventions

### Python Code
- Use Python 3.12+ features
- Follow PEP 8 style guide
- Use type hints where appropriate
- Keep functions focused and modular

### Configuration Management
- All API credentials should be configurable via config.json
- Never hardcode credentials or API keys
- Use environment variables for sensitive data when possible
- Validate configuration on startup

### Data Files
- CSV files are configured with `text eol=lf -whitespace` in .gitattributes, which allows trailing whitespace (this is expected for data files)
- Other text files use `text eol=lf` for consistent line endings
- If binary files are present, they are marked as binary in .gitattributes to prevent patch errors

### Git Practices
- CSV files are configured to ignore trailing whitespace errors
- Binary files are marked as binary to prevent patch errors
- See .gitattributes for file type handling rules
- Use .gitignore to exclude build artifacts, credentials, and temporary files

## Testing and Validation

### Before Committing
1. Ensure config.json is valid JSON
2. Verify Docker build succeeds: `docker build -t test .`
3. Test report generation if modifying visualization code
4. Verify integrations don't break if modifying API code

### Local Development
- Use virtual environments for Python dependencies
- Test with sample data before using production credentials
- Verify timezone handling (default: America/Chicago)

## Common Tasks

### Adding New Integrations
1. Add configuration section to config.json
2. Include `enabled` flag for toggling
3. Store credentials securely
4. Add error handling for API failures
5. Document the integration in this file

### Modifying Reports
1. Update visualization code in tools/ directory
2. Test with matplotlib dependencies
3. Ensure charts are saved as SVG (avoid committing binary image artifacts in PRs)
4. Update dashboard HTML if needed

### Changing Tracking Settings
1. Modify tracking section in config.json
2. Verify timezone handling
3. Test daily cutoff logic
4. Validate category priority ordering

## Important Notes

- **Timezone**: Default is America/Chicago - handle timezone conversions carefully
- **Data Retention**: Configured retention policies in config.json should be respected
- **Privacy**: This is a personal productivity tool - handle user data carefully
- **Error Handling**: API integrations should fail gracefully with helpful error messages
- **Credentials**: Never commit credentials to git - use credentials/ directory or environment variables

## File Patterns to Recognize

- `*.csv` - Data files (may have trailing whitespace)
- `*.svg` - Vector visualization files (preferred; avoid committing binaries in PRs)
- `config.json` - Main configuration (validate JSON syntax)
- `tools/*.py` - Python modules for data processing and reporting
- `gh-pages/` - Static web dashboard files
- `credentials/` - Sensitive credential files (never commit)
- `logs/` - Application logs and archives

## Best Practices for This Repository

1. **Minimal Changes**: Make surgical, focused changes to existing functionality
2. **Preserve Configuration**: Don't remove or modify working configuration options
3. **Test Integrations**: If changing integration code, verify it doesn't break existing setups
4. **Document Changes**: Update this file if adding new features or changing conventions
5. **Security First**: Always validate credentials handling and never log sensitive data
6. **Docker Compatibility**: Ensure changes work within the Docker container environment

## Git Workflow and Verification

### Non-Negotiables

#### No Unverifiable Claims
- Never say "pushed", "deployed", "fixed", "verified", "complete", or "made changes" unless you show the exact raw command output proving it

#### Always Show Raw Outputs
- For any git/deploy/network step, paste raw output exactly as printed (no paraphrase)
- If output is long, paste the relevant section plus command + exit code

#### One Change-Set at a Time
- Do not bundle multiple unrelated modifications
- Keep diffs small, focused, and reversible

#### Never git add -A
- Always stage targeted paths only
- If you must stage multiple files, list them explicitly

#### Trust but Verify
- Every "fix" ends with a verification checklist (commands + outputs)
- No verification = not done

### Standard Workflow

#### A) Diagnose Before Changing Anything
Run and paste raw outputs:
```bash
pwd
git status -sb
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git log -1 --oneline --decorate
git diff --name-status
```

#### B) Make the Change (Patch Discipline)
- Prefer minimal edits
- After editing, always show: `git diff`

#### C) Stage + Commit
Stage only intended files:
```bash
git add <exact paths>
git status --porcelain
git commit -m "<message>"
```
If "nothing to commit", stop and explain why (wrong files? already merged?)

## Railway Deployment Verification

### When Diagnosing "Site Still Old / Blank"

#### Prove What Railway is Serving Right Now
```bash
curl -I https://<railway-url>/dashboard.html
curl -s https://<railway-url>/dashboard.html | head -n 40
curl -s https://<railway-url>/dashboard.html | grep -n "raw.githubusercontent.com"
```

#### Verify JSON Availability from GitHub Raw
```bash
curl -I https://raw.githubusercontent.com/johnlicataptbiz/DailyAccomplishments/main/ActivityReport-$(date +%Y-%m-%d).json
```

#### Important Notes
- If Railway uses Docker static serving, assume redeploy is required for file changes to show up
- Railway auto-deploys when the `main` branch is updated (see docs/RAILWAY_DEPLOY.md)

## Frontend Robustness (Dashboard)

The dashboard implements the following fallback strategy (already implemented in gh-pages/dashboard.html):

1. Try same-origin `/ActivityReport-${date}.json`
2. Try same-origin `/reports/daily-report-${date}.json`
3. Fallback to GitHub raw: `https://raw.githubusercontent.com/johnlicataptbiz/DailyAccomplishments/main/ActivityReport-${date}.json`

All requests include:
- `cache: 'no-store'` header
- `?t=${Date.now()}` cache buster

The "View Raw Data" link points to the URL that actually succeeded.

**Important**: Never break gh-pages publishing; do not ignore ActivityReport-*.json.

## Reliability and Failure Handling

### Command Failures
- If a command fails, paste the full stderr and exit code
- If output is truncated, rerun inside bash -lc and pipe to a log:
  ```bash
  LOG=/tmp/agent_run.log; { <commands>; } 2>&1 | tee "$LOG"
  ```

### Authentication/Network Issues
- If auth/network prevents push/deploy, say so explicitly and provide the exact error

## Communication Style

When working on this repository:
- **Be short and concrete** - no fluff
- **Use checklists** to track progress
- **End each work block with**: "Next command I will run:" followed by exactly one command block
- **Show proof** - always paste raw command outputs for verification

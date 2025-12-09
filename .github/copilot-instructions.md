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

### Current Repository Layout
```
DailyAccomplishments/
├── .github/
│   └── copilot-instructions.md    # This file - Copilot agent instructions
├── .gitattributes                  # Git file handling rules
├── .gitignore                      # Excluded files and directories
├── config.json                     # Main configuration file
├── Dockerfile                      # Container build configuration
└── GIT_CONFIG_FIX.md              # Git configuration documentation
```

### Planned Directory Structure
As development progresses, the following structure will be implemented:
```
DailyAccomplishments/
├── tools/                          # Python modules (to be added)
│   ├── hubspot_collector.py       # HubSpot data collection
│   ├── aloware_collector.py       # Aloware data collection
│   ├── monday_collector.py        # Monday.com data collection
│   ├── slack_collector.py         # Slack data collection
│   ├── calendar_collector.py      # Google Calendar integration
│   ├── data_processor.py          # Data aggregation and categorization
│   ├── report_generator.py        # Report creation with visualizations
│   └── utils.py                    # Shared utilities
├── gh-pages/                       # Web dashboard (to be added)
│   ├── index.html                  # Dashboard home page
│   ├── styles.css                  # Styling
│   └── scripts.js                  # Client-side functionality
├── credentials/                    # API credentials (gitignored)
│   └── google_credentials.json    # Google Calendar OAuth credentials
├── logs/                           # Application logs (gitignored)
│   ├── daily/                      # Daily activity logs
│   └── archive/                    # Archived logs
└── tests/                          # Unit tests (to be added)
    └── test_*.py                   # Test files
```

### Configuration Files
- **config.json**: Main configuration file containing:
  - Tracking settings (hours, timezone, categories)
  - Integration credentials and settings
  - Report generation preferences
  - Notification settings (email, Slack webhooks)
  - Data retention policies

### File Handling
- **CSV files**: Data files that may contain trailing whitespace (configured in .gitattributes)
- **Binary files**: PNG/JPG images for reports and visualizations (marked as binary in .gitattributes)
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
- **Pillow**: For image processing
- System dependencies (installed in Docker): libfreetype6-dev, libpng-dev, libjpeg-dev, libopenjp2-7-dev, libtiff5-dev, tcl/tk for matplotlib and image processing

### Local Development Setup
For local development without Docker:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install Python dependencies
pip install matplotlib pillow

# Run the application (when Python code is added)
# python main.py  # or appropriate entry point
```

### Web Server
- Default port: 8000
- Serves reports and dashboard via Python's built-in HTTP server
- Static files served from `gh-pages/` directory

### Current Development Status
This repository is in active development. The core infrastructure (configuration, Docker setup, and instructions) is in place. Python modules for data collection, processing, and visualization will be added to the `tools/` directory as development progresses.

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
- Binary files (PNG, JPG) are marked as binary in .gitattributes to prevent patch errors

### Git Practices
- CSV files are configured to ignore trailing whitespace errors
- PNG/JPG files are marked as binary to prevent patch errors
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
2. Test with matplotlib and Pillow dependencies
3. Ensure images are saved as PNG (marked as binary)
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
- `*.png`, `*.jpg` - Binary visualization files
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

## Working with GitHub Copilot Coding Agent

When creating issues for Copilot to work on:

### Good Issue Types
- Bug fixes in data collection or processing logic
- Adding new integration modules following the established patterns
- Improving visualization and report generation
- Adding unit tests for existing functionality
- Documentation updates
- UI/UX improvements for the dashboard

### Issue Structure
Each issue should include:
- **Clear description**: What needs to be done and why
- **Acceptance criteria**: Specific requirements that must be met
- **File references**: Which files or modules are involved
- **Example data**: Sample inputs/outputs if applicable
- **Dependencies**: Any related issues or prerequisites

### Not Suitable for Copilot
- Complex architectural decisions
- Security-critical credential handling
- Major refactoring across multiple integrations
- Changes requiring deep domain knowledge of specific APIs

### Development Workflow
1. Issues assigned to @copilot will be worked on automatically
2. Copilot will create a branch and draft PR
3. Review PR and provide feedback via comments mentioning @copilot
4. Copilot will iterate based on feedback
5. Merge when ready after human review

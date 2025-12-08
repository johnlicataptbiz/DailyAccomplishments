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
- Additional system dependencies: freetype, libpng, libjpeg for matplotlib

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
- CSV files may have trailing whitespace (this is expected)
- Use consistent line endings (LF) for text files
- Binary files (images) should be treated as binary, not text

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

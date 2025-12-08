# Copilot Instructions

## Project Overview

DailyAccomplishments is a productivity tracking system that integrates with multiple platforms to monitor and report daily activities. The system tracks time-based activities across various categories and provides reporting capabilities.

## Configuration Management

### Config File Structure
- All configuration is stored in `config.json` at the repository root
- Configuration includes tracking settings, reporting options, and integration credentials
- Never commit actual API keys, tokens, or passwords to the repository

### Key Configuration Sections
1. **tracking**: Daily activity tracking settings (timezone, hours, log directories)
2. **report**: Report generation settings (coverage times, formatting options)
3. **category_priority**: Ordered list of activity categories (Coding, Research, Communication, Other, Meetings)
4. **retention**: Log and report retention policies
5. **notifications**: Email and Slack webhook configurations
6. **integrations**: HubSpot, Aloware, Monday.com, Slack, and Google Calendar

## Integration Setup

### Supported Integrations
- **HubSpot**: CRM integration for contact and activity tracking
- **Aloware**: Communication platform integration
- **Monday.com**: Project management integration
- **Slack**: Team communication and notifications
- **Google Calendar**: Calendar event tracking

### Configuration Pattern
Each integration follows this structure:
```json
{
  "integration_name": {
    "enabled": true/false,
    "credentials": "..."  // API keys, tokens, etc.
  }
}
```

## Code Style and Conventions

### JSON Configuration
- Use 2-space indentation for JSON files
- Keep configuration keys in snake_case
- Group related settings under logical parent objects
- Maintain alphabetical order within configuration sections where practical

### File Organization
- Configuration: Repository root (`config.json`)
- Logs: `logs/daily/` for daily logs, `logs/archive/` for archived logs
- Credentials: `credentials/` directory for sensitive files (should be gitignored)

## Security Best Practices

### Handling Sensitive Data
1. **Never commit real credentials**: All API keys, tokens, passwords, and sensitive data must be placeholder values or empty strings in the repository
2. **Use environment variables**: For deployment, use environment variables or secure secret management
3. **Credential files**: Store OAuth credentials (like Google Calendar) in the `credentials/` directory and ensure this directory is in `.gitignore`
4. **Configuration template**: The `config.json` serves as a template - users should copy and populate with their actual credentials locally

### Example Placeholders
- `access_token: ""` - Empty string for tokens
- `api_key: ""` - Empty string for API keys
- `password: "your-app-password"` - Descriptive placeholder
- `username: "your-email@gmail.com"` - Example format

## Development Guidelines

### Making Changes
- When modifying configuration structure, update all relevant sections
- Maintain backward compatibility when possible
- Document new configuration options clearly
- Test integration settings don't break with empty/disabled configurations

### Adding New Integrations
1. Add integration config section to `config.json`
2. Include `enabled` boolean flag
3. Use empty strings for credential placeholders
4. Update this documentation with integration details
5. Follow existing naming conventions (snake_case for keys)

## Testing and Validation

### Configuration Validation
- Ensure JSON is valid and properly formatted
- Verify all required fields are present
- Check that disabled integrations can be safely ignored
- Validate timezone format (e.g., "America/Chicago")
- Verify time format (24-hour: "HH:MM")

### Before Committing
- Remove any actual credentials
- Verify JSON syntax with a linter
- Ensure file endings are consistent (LF)
- Check that placeholder values are clear and descriptive

# DailyAccomplishments

A productivity tracking system that integrates with various platforms.

## Security

This repository has security scanning enabled. Please see [SECURITY.md](SECURITY.md) for our security policy and best practices.

### Secret Scanning

GitHub Secret Scanning is enabled for this repository to automatically detect accidentally committed secrets. If you attempt to push code containing secrets, you may see a push protection warning.

**Important**: Never commit actual credentials to this repository.

## Configuration

The `config.json` file contains placeholder values for various API integrations:

- HubSpot
- Aloware
- Monday.com
- Slack
- Google Calendar
- Email notifications

### Setup

1. Copy `config.json` to create your local configuration
2. Replace placeholder values with your actual credentials
3. Ensure sensitive credentials are stored securely (environment variables recommended)
4. Never commit actual API keys or tokens

## Contributing

When contributing to this repository:

1. Review the [SECURITY.md](SECURITY.md) file
2. Ensure no secrets are committed
3. Use environment variables or secure secret management
4. Follow the security best practices outlined in the documentation

## Support

For security issues, please follow the reporting guidelines in [SECURITY.md](SECURITY.md).

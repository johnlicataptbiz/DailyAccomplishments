# Security Policy

## Supported Versions

We take security seriously in the DailyAccomplishments project.

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please follow these steps:

1. **Do not** open a public issue
2. Send details to the repository maintainers privately
3. Include details about the vulnerability and steps to reproduce

We will respond to security reports within 48 hours.

## Secret Scanning

This repository has secret scanning enabled to detect accidentally committed secrets such as:

- API keys
- Access tokens
- Passwords
- Private keys
- OAuth tokens

### What to do if a secret is detected:

1. **Immediately rotate** the exposed credential
2. Remove the secret from the repository history
3. Review who might have accessed the exposed secret
4. Update your local configuration to use environment variables or secure secret management

### Best Practices:

- Never commit secrets directly in code
- Use environment variables for sensitive configuration
- Store credentials in `credentials/` directory (which is gitignored)
- Use `.env` files for local development (ensure they're in `.gitignore`)
- Review the `config.json.example` for proper configuration structure

## Secure Configuration

The `config.json.example` file contains placeholders for sensitive information. Ensure you:

1. Copy `config.json.example` to `config.json` in your local environment
2. Fill in actual credentials in your local `config.json`
3. Never commit actual credentials to the repository
4. Use the provided placeholder values in the example file as a template

### Protected Credentials:

- HubSpot access tokens
- Aloware API keys
- Monday.com API tokens
- Slack bot/user tokens
- Google Calendar credentials
- Email passwords
- Webhook URLs

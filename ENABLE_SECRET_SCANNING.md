# Enabling Secret Scanning - Administrator Guide

This repository has been configured with the necessary files to support GitHub Secret Scanning. To fully enable secret scanning, a repository administrator needs to complete the following steps in the GitHub web interface:

## Steps to Enable Secret Scanning

### 1. Navigate to Repository Settings

1. Go to https://github.com/johnlicataptbiz/DailyAccomplishments
2. Click on **Settings** (tab at the top of the repository)

### 2. Access Code Security Settings

1. In the left sidebar, scroll down to **Code security and analysis**
2. Click on **Code security and analysis**

### 3. Enable Secret Scanning

Find the **Secret scanning** section and:

1. Click **Enable** next to "Secret scanning"
2. This will allow GitHub to scan the repository for accidentally committed secrets

### 4. Enable Push Protection (Recommended)

In the same section:

1. Click **Enable** next to "Push protection"
2. This prevents new secrets from being pushed to the repository
3. When a secret is detected during a push, GitHub will block it and provide options to:
   - Cancel the push
   - Review the secret
   - Bypass the protection (not recommended unless it's a false positive)

### 5. Review and Unblock Detected Secrets

If you received the URL: `https://github.com/johnlicataptbiz/DailyAccomplishments/security/secret-scanning/unblock-secret/36YNLRzes4ROdOt3nS0n3I9gjPb`

This indicates a secret was detected. To review it:

1. Click on the URL or navigate to **Security** tab > **Secret scanning**
2. Review the detected secret
3. If it's a legitimate secret that was accidentally committed:
   - **First**: Rotate/revoke the secret immediately in the service it belongs to
   - **Then**: Remove it from the repository (already done via config.json cleanup)
   - Mark the alert as "Revoked" or "Closed"
4. If it's a false positive:
   - You can mark it as such
   - Consider adding a custom pattern exemption if needed

### 6. Enable Dependabot (Optional but Recommended)

While in Code security and analysis:

1. Enable **Dependabot alerts** - to get notifications about vulnerabilities in dependencies
2. Enable **Dependabot security updates** - to automatically create PRs to update vulnerable dependencies

### 7. Review CodeQL Scanning

The repository now includes a CodeQL workflow (`.github/workflows/codeql.yml`) that will:

- Run automatically on pushes to main/master branches
- Run on pull requests
- Run weekly on a schedule
- Scan for security vulnerabilities in code

To verify it's working:
1. Navigate to **Actions** tab
2. Look for "CodeQL Security Scanning" workflow
3. Check that it runs successfully

## What Has Been Done

This pull request has added the following files to support secret scanning:

1. **SECURITY.md** - Security policy and guidelines for the repository
2. **.gitignore** - Prevents sensitive files from being committed
3. **README.md** - Documentation about security and configuration
4. **config.json.example** - Template configuration file without secrets
5. **.github/secret_scanning.yml** - Secret scanning configuration
6. **.github/workflows/codeql.yml** - Automated code security scanning

## Best Practices Going Forward

1. **Never commit secrets** - Use environment variables or secure secret management
2. **Use .env files** for local development (they're already in .gitignore)
3. **Rotate any exposed credentials** immediately
4. **Review security alerts** regularly in the Security tab
5. **Keep dependencies updated** to avoid security vulnerabilities

## Troubleshooting

### If push protection blocks a legitimate commit:

1. Review the detected secret
2. If it's a false positive, you can bypass protection (use with caution)
3. Consider using test/dummy values that don't match secret patterns

### If you need to check for secrets locally:

Use tools like:
- `git-secrets` - AWS's tool for preventing secrets
- `truffleHog` - Scans git history for secrets
- `detect-secrets` - Yelp's tool for preventing secrets

## Additional Resources

- [GitHub Secret Scanning Documentation](https://docs.github.com/en/code-security/secret-scanning)
- [About Push Protection](https://docs.github.com/en/code-security/secret-scanning/push-protection-for-repositories-and-organizations)
- [Supported Secret Patterns](https://docs.github.com/en/code-security/secret-scanning/secret-scanning-patterns)

---

After completing these steps, secret scanning will be fully enabled and active for this repository.

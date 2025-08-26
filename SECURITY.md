# Security Policy

## Supported Versions

We actively support the following versions of MaterialsCodeGraph-lite with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously and appreciate your help in keeping MCG-lite secure.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing: **security@mcg-project.org**

You should receive a response within 24 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

### What to Include

Please include the following information in your report:

1. **Description**: Brief description of the vulnerability
2. **Impact**: What an attacker could accomplish by exploiting this vulnerability
3. **Reproduction**: Step-by-step instructions to reproduce the issue
4. **Environment**: Version of MCG-lite, Python version, operating system
5. **Mitigation**: Any temporary mitigations you've identified (if applicable)

### Response Process

1. **Acknowledgment**: We'll acknowledge receipt of your vulnerability report within 24 hours
2. **Investigation**: We'll investigate and assess the severity within 72 hours
3. **Fix Development**: We'll work on a fix and coordinate disclosure timeline with you
4. **Release**: We'll release a patched version and publish security advisory
5. **Recognition**: We'll acknowledge your contribution (if desired) in our security acknowledgments

## Security Best Practices

### For Users

When using MCG-lite in production:

1. **Environment Variables**: Store API keys and secrets in environment variables, never in code
2. **Network Security**: Use HTTPS for all external communications
3. **Input Validation**: Validate all user inputs, especially natural language tasks
4. **Access Control**: Implement proper authentication and authorization
5. **Updates**: Keep MCG-lite and its dependencies up to date
6. **Monitoring**: Monitor for unusual activity or unexpected resource usage

### For Developers

When contributing to MCG-lite:

1. **Secrets**: Never commit API keys, passwords, or other secrets
2. **Input Sanitization**: Sanitize all user inputs before processing
3. **Dependencies**: Regularly update dependencies and check for known vulnerabilities
4. **Code Review**: All changes require code review before merging
5. **Testing**: Include security test cases for new features

## Known Security Considerations

### API Keys
- Materials Project API keys are stored in environment variables
- Keys are never logged or included in error messages
- Consider key rotation policies for production deployments

### Natural Language Processing
- User-provided natural language tasks are parsed but not executed as code
- Input validation prevents injection attacks
- Rate limiting recommended for production deployments

### File Operations
- All file operations use absolute paths to prevent directory traversal
- Temporary files are created in secure temporary directories
- File permissions are set restrictively

### Container Security
- Simulation containers run with minimal privileges
- Container images should be regularly updated
- Resource limits prevent DoS attacks

## Security Updates

Security updates will be released as patch versions and will include:

1. **Security Advisory**: Published on GitHub Security Advisories
2. **CHANGELOG**: Documented in CHANGELOG.md with security tag
3. **Release Notes**: Detailed information about the fix
4. **Migration Guide**: If configuration changes are required

## Security Acknowledgments

We thank the following individuals for responsibly disclosing security vulnerabilities:

<!-- This section will be updated as we receive reports -->
*None reported yet*

## Contact

For questions about this security policy, contact: security@mcg-project.org

---

**Remember: Security is a shared responsibility. Thank you for helping keep MCG-lite secure!** 🔒
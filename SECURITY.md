# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

The CIRCE Python team takes security bugs seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

📧 **[Security contact to be determined - please create an issue for now]**

If you prefer, you can also report vulnerabilities through:
- GitHub Security Advisories: https://github.com/OHDSI/circe-be-python/security/advisories/new

### What to Include

To help us triage and address the issue as quickly as possible, please include:

1. **Type of issue** (e.g., SQL injection, code execution, etc.)
2. **Full paths of source file(s)** related to the issue
3. **Location of the affected source code** (tag/branch/commit or direct URL)
4. **Step-by-step instructions** to reproduce the issue
5. **Proof-of-concept or exploit code** (if possible)
6. **Impact of the issue**, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: We will acknowledge receipt of your report within 48 hours
- **Status Update**: We will provide a more detailed response within 7 days
- **Fix Timeline**: We aim to release a fix within 30 days of disclosure for critical issues

### Disclosure Policy

- Security issues will be disclosed **after** a fix has been released
- We follow a **coordinated disclosure** process
- We will credit reporters unless they wish to remain anonymous

## Security Considerations

### SQL Injection

The CIRCE Python package generates SQL from cohort definitions. While the package:

- ✅ Uses parameterized templates for SQL generation
- ✅ Validates input structure using Pydantic
- ✅ Does not execute SQL directly

Users should be aware:

- ⚠️ **Never run generated SQL from untrusted sources** without review
- ⚠️ **Always validate cohort JSON** before generating SQL
- ⚠️ **Review generated SQL** before executing in production databases
- ⚠️ **Use least-privilege database accounts** when executing cohort SQL

### Code Execution

The package:

- ✅ Does not execute arbitrary code from cohort definitions
- ✅ Does not eval() or exec() user input
- ✅ Uses safe deserialization (Pydantic models)

### Dependency Security

We regularly monitor and update dependencies for security vulnerabilities:

- Pydantic (>=2.0.0) - Data validation
- typing-extensions (>=4.0.0) - Type hints

Run `pip install --upgrade ohdsi-circe` to get the latest security updates.

## Best Practices for Users

1. **Validate Input**: Always validate cohort definitions before processing:
   ```python
   from circe.check.check import check_cohort_expression
   warnings = check_cohort_expression(cohort)
   ```

2. **Review Generated SQL**: Inspect SQL before execution, especially for production databases

3. **Use Version Pinning**: Pin package versions in production:
   ```
   ohdsi-circe==1.0.0
   ```

4. **Keep Updated**: Regularly update to the latest version for security patches

5. **Least Privilege**: Execute cohort SQL with minimal database permissions

6. **Audit Logs**: Monitor cohort definition sources and SQL execution

## Known Limitations

- The package does not sanitize concept IDs or codeset IDs in generated SQL
- SQL is generated as text; users must review before execution
- No built-in query execution capabilities (by design)

## Security Updates

Security updates will be announced through:

- GitHub Security Advisories
- Release notes in CHANGELOG.md
- PyPI release announcements

Subscribe to GitHub notifications to stay informed.

## Acknowledgments

We thank the security research community for their contributions to making CIRCE Python more secure.

## Questions?

For non-security-related questions, please use:
- GitHub Issues: https://github.com/OHDSI/circe-be-python/issues
- GitHub Discussions: https://github.com/OHDSI/circe-be-python/discussions

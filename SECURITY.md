# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| v1.x (latest) | ✅ |
| < v1.0 | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability in SessionPilot, please report it responsibly.

**Do NOT open a public issue.**

Instead, use one of these options:

1. **GitHub Security Advisory** (preferred): [Report a vulnerability](https://github.com/web-werkstatt/session-pilot/security/advisories/new)
2. **Email**: security@web-werkstatt.at

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

### What to expect

- Acknowledgment within **48 hours**
- Status update within **7 days**
- Fix and disclosure within **30 days** (coordinated)

### Scope

SessionPilot is a **self-hosted** application. Security issues we care about:

- SQL injection, XSS, CSRF in the web interface
- Path traversal in file access (documents, exports)
- Authentication bypass (if auth is added in the future)
- Sensitive data exposure in API responses
- Docker container escape or privilege escalation

### Out of Scope

- Issues in third-party dependencies (report upstream, Dependabot handles updates)
- Denial of service on a self-hosted instance (you control your own server)
- Social engineering

## Security Best Practices for Users

- Run SessionPilot behind a reverse proxy (Caddy, nginx) with HTTPS
- Do not expose port 5055 directly to the internet
- Keep your `.env` file private (it contains database credentials)
- Use strong database passwords
- Keep dependencies updated (`git pull && pip install -r requirements.txt`)
